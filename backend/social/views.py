from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Comment, Conversation, Follow, Like, Notification, Post, Reel, SavedPost, Story
from .serializers import (
    CommentSerializer,
    ConversationSerializer,
    MessageSerializer,
    NotificationSerializer,
    PostSerializer,
    ProfileSerializer,
    ReelSerializer,
    RegisterSerializer,
    StorySerializer,
    UserSerializer,
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "author", None) or getattr(obj, "user", None)
        return owner == request.user


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    if request.method == "PATCH":
        serializer = ProfileSerializer(request.user.profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(UserSerializer(request.user, context={"request": request}).data)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.select_related("profile").all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "profile__display_name", "profile__bio"]

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, pk=None):
        target = self.get_object()
        if target == request.user:
            return Response({"detail": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if created and target != request.user:
            Notification.objects.create(recipient=target, actor=request.user, verb=Notification.FOLLOW)
        return Response({"following": True})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def unfollow(self, request, pk=None):
        target = self.get_object()
        Follow.objects.filter(follower=request.user, following=target).delete()
        return Response({"following": False})


class PostViewSet(viewsets.ModelViewSet):
    queryset = (
        Post.objects.select_related("author", "author__profile")
        .prefetch_related("comments", "comments__author", "likes", "saved_by", "hashtags")
        .all()
    )
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ["caption", "author__username", "hashtags__name"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=["get"])
    def feed(self, request):
        following = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True) if request.user.is_authenticated else []
        queryset = self.get_queryset().filter(Q(author__in=following) | Q(author=request.user)) if request.user.is_authenticated else self.get_queryset()
        return self._paginated(queryset)

    @action(detail=False, methods=["get"])
    def explore(self, request):
        queryset = self.get_queryset().annotate(score=Count("likes") + Count("comments")).order_by("-score", "-created_at")
        return self._paginated(queryset)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if created and post.author != request.user:
            Notification.objects.create(recipient=post.author, actor=request.user, verb=Notification.LIKE, post=post)
        return Response({"liked": True})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request, pk=None):
        Like.objects.filter(post=self.get_object(), user=request.user).delete()
        return Response({"liked": False})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def save(self, request, pk=None):
        SavedPost.objects.get_or_create(post=self.get_object(), user=request.user)
        return Response({"saved": True})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def unsave(self, request, pk=None):
        SavedPost.objects.filter(post=self.get_object(), user=request.user).delete()
        return Response({"saved": False})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def share(self, request, pk=None):
        return Response({"share_url": request.build_absolute_uri(f"/posts/{self.get_object().id}")})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def comments(self, request, pk=None):
        post = self.get_object()
        serializer = CommentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post, author=request.user)
        if post.author != request.user:
            Notification.objects.create(recipient=post.author, actor=request.user, verb=Notification.COMMENT, post=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _paginated(self, queryset):
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class StoryViewSet(viewsets.ModelViewSet):
    queryset = Story.objects.select_related("author", "author__profile").filter(expires_at__gt=timezone.now())
    serializer_class = StorySerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ReelViewSet(viewsets.ModelViewSet):
    queryset = Reel.objects.select_related("author", "author__profile").all()
    serializer_class = ReelSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related("actor", "actor__profile", "post")

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({"ok": True})


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related("participants", "messages")

    def perform_create(self, serializer):
        conversation = serializer.save()
        conversation.participants.add(self.request.user)

    @action(detail=True, methods=["post"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(conversation=conversation, sender=request.user)
        for recipient in conversation.participants.exclude(id=request.user.id):
            Notification.objects.create(recipient=recipient, actor=request.user, verb=Notification.MESSAGE)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def search(request):
    query = request.query_params.get("q", "")
    users = User.objects.filter(Q(username__icontains=query) | Q(profile__display_name__icontains=query))[:10]
    posts = Post.objects.filter(Q(caption__icontains=query) | Q(hashtags__name__icontains=query)).distinct()[:10]
    return Response(
        {
            "users": UserSerializer(users, many=True, context={"request": request}).data,
            "posts": PostSerializer(posts, many=True, context={"request": request}).data,
        }
    )
