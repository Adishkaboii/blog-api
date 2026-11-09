from django.db.models import Count

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag


def draft_posts_badge(request):
    return Post.objects.filter(
        status=Post.Status.DRAFT
    ).count()


def dashboard_callback(request, context):
    total_posts = Post.objects.count()

    published_posts = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).count()

    draft_posts = total_posts - published_posts

    published_percentage = (
        round(published_posts / total_posts * 100)
        if total_posts
        else 0
    )

    categories = list(
        Category.objects.annotate(
            posts_count=Count("posts")
        ).order_by("-posts_count", "name")
    )

    max_category_posts = max(
        (category.posts_count for category in categories),
        default=0,
    )

    category_stats = [
        {
            "name": category.name,
            "count": category.posts_count,
            "percentage": (
                round(category.posts_count / max_category_posts * 100)
                if max_category_posts
                else 0
            ),
        }
        for category in categories
    ]

    top_authors = (
        User.objects.annotate(
            posts_count=Count("posts")
        )
        .filter(posts_count__gt=0)
        .order_by("-posts_count", "email")[:5]
    )

    context.update(
        {
            "users_count": User.objects.count(),
            "posts_count": total_posts,
            "comments_count": Comment.objects.count(),
            "categories_count": Category.objects.count(),
            "tags_count": Tag.objects.count(),
            "published_count": published_posts,
            "draft_count": draft_posts,
            "published_percentage": published_percentage,
            "category_stats": category_stats,
            "top_authors": top_authors,
        }
    )

    return context