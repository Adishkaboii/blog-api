from typing import ClassVar

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django_summernote.widgets import SummernoteWidget
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
    list_display = ("id", "name", "slug", "expandable_posts",)
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
        ).prefetch_related("posts")

    @admin.display(description="Posts", ordering="posts_count")
    def expandable_posts(self, obj):
        posts = list(obj.posts.all())

        if not posts:
            return "0 posts"

        items = format_html_join(
            "",
            "<li class='py-1'>{}</li>",
            ((post.title,) for post in posts),
        )

        return format_html(
            '<details><summary class="cursor-pointer">{} posts</summary>'
            '<ul class="mt-2">{}</ul></details>',
            len(posts),
            items,
        )

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("id", "name", "slug", "expandable_posts",)
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
        ).prefetch_related("posts")
    @admin.display(description="Posts", ordering="posts_count")
    def expandable_posts(self, obj):
        posts = list(obj.posts.all())

        if not posts:
            return "0 posts"

        items = format_html_join(
            "",
            "<li class='py-1'>{}</li>",
            ((post.title,) for post in posts),
        )

        return format_html(
            '<details><summary class="cursor-pointer">{} posts</summary>'
            '<ul class="mt-2">{}</ul></details>',
            len(posts),
            items,
        )

class CommentInline(TabularInline):
    model = Comment
    extra = 0
    per_page = 10
    tab = True

    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    show_change_link = True

class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = "__all__"
        widgets: ClassVar[dict] = {
            "body": SummernoteWidget(),
        }


@admin.register(Post)
class PostAdmin(ModelAdmin):
    autocomplete_fields = ("author", "category")
    inlines = (CommentInline,)
    actions_row = ("publish_single", "draft_single")
    actions_list = ("publish_all_drafts",)
    form = PostAdminForm
    change_form_template = "blog/post_change_form.html"
    actions = ("publish_posts", "unpublish_posts")
    list_display = (
        "id",
        "title",
        "author",
        "category",
        "colored_status",
        "expandable_comments",
        "created_at",
    )

    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("author", RelatedDropdownFilter),
        ("tags", RelatedDropdownFilter),
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
    
    @action(
        description="Publish all drafts",
        icon="publish",
        permissions=["change"],
        dialog={
            "title": "Publish all drafts?",
            "description": "All draft posts will become published.",
            "submit_text": "Publish all",
        },
    )
    def publish_all_drafts(self, request, form):
        updated = Post.objects.filter(
            status=Post.Status.DRAFT
        ).update(status=Post.Status.PUBLISHED)

        self.message_user(
            request,
            f"{updated} draft posts published successfully.",
        )

        return HttpResponse(
            headers={
                "HX-Redirect": reverse("admin:blog_post_changelist"),
            }
        )
    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        context["show_save_and_publish"] = True
        return super().render_change_form(
            request, context, add, change, form_url, obj
        )
    
    @admin.display(description="Comments")
    def expandable_comments(self, obj):
        comments = list(obj.comments.all())

        if not comments:
            return "0 comments"

        items = format_html_join(
            "",
            "<li class='py-1'><strong>{}</strong>: {}</li>",
            (
                (comment.author.email, comment.body)
                for comment in comments
            ),
        )

        return format_html(
            '<details class="min-w-48">'
            '<summary class="cursor-pointer">{} comments</summary>'
            '<ul class="mt-2 space-y-1">{}</ul>'
            "</details>",
            len(comments),
            items,
        )

    def save_model(self, request, obj, form, change):
        if "_save_and_publish" in request.POST:
            obj.status = Post.Status.PUBLISHED

        super().save_model(request, obj, form, change)


    fieldsets = (
        (
            "Content",
            {
                "fields": ("title", "body"),
                "classes": ("tab",),
            },
        ),
        (
            "Classification",
            {
                "fields": ("category", "tags", "status"),
                "classes": ("tab",),
            },
        ),
        (
            "Meta",
            {
                "fields": ("slug", "author"),
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

        return (
            queryset
            .annotate(comments_count=Count("comments"))
            .prefetch_related("comments__author")
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