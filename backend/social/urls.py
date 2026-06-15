from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, NotificationViewSet, PostViewSet, ReelViewSet, StoryViewSet, UserViewSet, me, register, search

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("posts", PostViewSet, basename="posts")
router.register("stories", StoryViewSet, basename="stories")
router.register("reels", ReelViewSet, basename="reels")
router.register("notifications", NotificationViewSet, basename="notifications")
router.register("conversations", ConversationViewSet, basename="conversations")

urlpatterns = [
    path("auth/register/", register, name="register"),
    path("me/", me, name="me"),
    path("search/", search, name="search"),
    path("", include(router.urls)),
]
