from typing import ClassVar

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import action

from apps.blog.models import Category, Comment, Post, Tag


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("id", "name", "slug", "posts_count",)
    search_fields = ("name",)
    ordering = ("name",)
    prepopulated_fields: ClassVar[dict] = {
        "slug": ("name",)
    }

    @admin.display(
        description="Posts",
        ordering="posts_count",
    )
    def posts_count(self, obj: Category) -> int:
        return obj.posts_count
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.annotate(
            posts_count=Count("posts")
        )


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("id", "name", "slug", "posts_count",)
    search_fields = ("name",)
    ordering = ("name",)
    prepopulated_fields: ClassVar[dict] = {
        "slug": ("name",)
    }

    @admin.display(
        description="Posts",
        ordering="posts_count",
    )
    def posts_count(self, obj: Tag) -> int:
        return obj.posts_count
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.annotate(
            posts_count=Count("posts")
        )

class CommentInline(TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    show_change_link = True



@admin.register(Post)
class PostAdmin(ModelAdmin):
    autocomplete_fields = ("author", "category")
    inlines = (CommentInline,)
    actions_row = ("publish_single", "draft_single")
    actions = ("publish_posts", "unpublish_posts")
    list_display = (
        "id",
        "title",
        "author",
        "category",
        "colored_status",
        "comments_count",
        "created_at",
    )

    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("created_at", RangeDateFilter),
    )
    search_fields = ("title", "body", "author__email")

    prepopulated_fields: ClassVar[dict] = {
        "slug": ("title",)
    }

    filter_horizontal = ("tags",)
    list_select_related = ("author", "category")

    @action(description="Publish", url_path="publish")
    def publish_single(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        
        post = self.get_object(request, object_id)

        if post is not None:
            if not self.has_change_permission(request, post):
                raise PermissionDenied

            post.status = Post.Status.PUBLISHED
            post.save(update_fields=["status"])

            self.message_user(request, "Post published successfully.")

        return HttpResponseRedirect(
            reverse("admin:blog_post_changelist")
        )


    @action(description="Draft", url_path="draft")
    def draft_single(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        
        post = self.get_object(request, object_id)

        if post is not None:
            if not self.has_change_permission(request, post):
                raise PermissionDenied
            
            post.status = Post.Status.DRAFT
            post.save(update_fields=["status"])

            self.message_user(request, "Post moved to drafts.")

        return HttpResponseRedirect(
            reverse("admin:blog_post_changelist")
        )


    fieldsets = (
        (
            "Post information",
            {
                "fields": (
                    "title",
                    "slug",
                    "body",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Publishing",
            {
                "fields": (
                    "author",
                    "category",
                    "tags",
                    "status",
                ),
                "classes": ("tab",),
            },
        ),
    )



    @admin.display(description="Status", ordering="status")
    def colored_status(self, obj: Post) -> str:
        if obj.status == Post.Status.PUBLISHED:
            color = "#22c55e"
            label = "Published"
        else:
            color = "#f59e0b"
            label = "Draft"

        return format_html(
            '<span style="color: {}; font-weight: bold;">'
            '● {}</span>',
            color,
            label,
        )

    @admin.display(description="Comments", ordering="comments_count")
    def comments_count(self, obj: Post) -> int:
        return obj.comments_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            comments_count=Count("comments")
        )
    
    @action(description="Publish selected posts")
    def publish_posts(self, request, queryset):
        updated = queryset.update(
            status=Post.Status.PUBLISHED
        )

        self.message_user(
            request,
            f"{updated} posts published successfully.",
        )

    @action(description="Move selected posts to drafts")
    def unpublish_posts(self, request, queryset):
        updated = queryset.update(
            status=Post.Status.DRAFT
        )

        self.message_user(
            request,
            f"{updated} posts moved to drafts.",
        )




@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("id", "short_body", "author", "post", "created_at")
    list_filter = (
        ("created_at", RangeDateFilter),
        ("post", RelatedDropdownFilter),
    )
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("author", "post")
    list_select_related = ("author", "post")

    ordering = ("-created_at",)

    @admin.display(description="Comment")
    def short_body(self, obj: Comment) -> str:
        if len(obj.body) > 60:
            return obj.body[:60] + "..."

        return obj.body