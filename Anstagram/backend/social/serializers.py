import re

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from .models import Comment, Conversation, Follow, Hashtag, Message, Notification, Post, Profile, Reel, SavedPost, Story


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Profile.objects.get_or_create(user=user, defaults={"display_name": user.username})
        return user


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    followers_count = serializers.IntegerField(source="user.follower_edges.count", read_only=True)
    following_count = serializers.IntegerField(source="user.following_edges.count", read_only=True)
    posts_count = serializers.IntegerField(source="user.posts.count", read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "display_name",
            "bio",
            "avatar",
            "website",
            "is_private",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
        ]

    def get_is_following(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and Follow.objects.filter(follower=request.user, following=obj.user).exists())


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "text", "created_at"]
        read_only_fields = ["post", "author", "created_at"]


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    hashtags = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)
    saved_count = serializers.IntegerField(source="saved_by.count", read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "caption",
            "image",
            "hashtags",
            "location",
            "likes_count",
            "comments_count",
            "saved_count",
            "is_liked",
            "is_saved",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "created_at", "updated_at"]

    def get_is_liked(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.likes.filter(user=request.user).exists())

    def get_is_saved(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.saved_by.filter(user=request.user).exists())

    def create(self, validated_data):
        post = Post.objects.create(**validated_data)
        for tag in set(re.findall(r"#(\w+)", post.caption)):
            hashtag, _ = Hashtag.objects.get_or_create(name=tag.lower(), defaults={"slug": tag.lower()})
            post.hashtags.add(hashtag)
        return post


class StorySerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ["id", "author", "media", "caption", "expires_at", "is_expired", "created_at"]
        read_only_fields = ["author", "created_at"]

    def get_is_expired(self, obj):
        return obj.expires_at <= timezone.now()


class ReelSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Reel
        fields = ["id", "author", "video", "caption", "created_at"]
        read_only_fields = ["author", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "actor", "verb", "post", "is_read", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "body", "created_at"]
        read_only_fields = ["sender", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    participant_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "participants", "participant_ids", "messages", "created_at", "updated_at"]

    def create(self, validated_data):
        participants = validated_data.pop("participant_ids")
        conversation = Conversation.objects.create()
        conversation.participants.set(participants)
        return conversation
