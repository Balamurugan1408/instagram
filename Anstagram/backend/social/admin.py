from django.contrib import admin

from .models import Comment, Conversation, Follow, Hashtag, Like, Message, Notification, Post, Profile, Reel, SavedPost, Story

admin.site.register(Profile)
admin.site.register(Follow)
admin.site.register(Hashtag)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(SavedPost)
admin.site.register(Story)
admin.site.register(Reel)
admin.site.register(Notification)
admin.site.register(Conversation)
admin.site.register(Message)
