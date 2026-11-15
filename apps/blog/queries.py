from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    CharField,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

PAGE_SIZE = 10
NEWEST_POSTS_LIMIT = 5


def categories_by_name() -> QuerySet[Category]:
    """Return all categories ordered by name."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Return published posts ordered by newest first."""
    return Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).order_by("-created_at")


def newest_published_posts() -> QuerySet[Post]:
    """Return the five newest published posts."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """Return a post by slug or None if it does not exist."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Count active users excluding staff users."""
    return User.objects.filter(
        is_active=True,
        is_staff=False,
    ).count()


def has_drafts() -> bool:
    """Return True if at least one draft post exists."""
    return Post.objects.filter(
        status=Post.Status.DRAFT
    ).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Return one page of published posts."""
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return published_posts()[start:end]


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Return posts whose titles contain the word."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Return users with the given email domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Return posts without a category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Return categories matching any of the given slugs."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Return posts created in a specific month and year."""
    return Post.objects.filter(
        created_at__year=year,
        created_at__month=month,
    )


def posts_last_days(days: int) -> QuerySet[Post]:
    """Return posts created within the last number of days."""
    cutoff = timezone.now() - timedelta(days=days)
    return Post.objects.filter(created_at__gte=cutoff)


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Return posts created between two inclusive dates."""
    return Post.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

def author_published_posts(email: str) -> QuerySet[Post]:
    """Return published posts by given author."""
    return Post.objects.filter(
        status=Post.Status.PUBLISHED,
        author__email__iexact=email,
    )

def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Return posts with given tag."""
    return Post.objects.filter(
        tags__slug=tag_slug,
    )

def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Return comments for posts in given category."""
    return Comment.objects.filter(
        post__category__slug=category_slug,
    )

def users_with_published_posts() -> QuerySet[User]:
    """Return users who have published posts."""
    return User.objects.filter(
        posts__status=Post.Status.PUBLISHED,
    ).distinct()

def posts_without_tags() -> QuerySet[Post]:
    """Return posts without any tags."""
    return Post.objects.filter(tags__isnull=True)

def users_without_comments() -> QuerySet[User]:
    """Return users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)

def posts_with_both_tags(
    first_slug: str,
    second_slug: str,
) -> QuerySet[Post]:
    """Return posts containing both specified tags."""
    return Post.objects.filter(
        tags__slug=first_slug
    ).filter(
        tags__slug=second_slug
    ).distinct()

def search_posts(text: str) -> QuerySet[Post]:
    """Return posts by the title or body."""
    return Post.objects.filter(
        Q(title__icontains=text) | Q(body__icontains=text)
    )

def published_posts_missing_info() -> QuerySet[Post]:
    """Return published posts with missing category or tags."""
    return Post.objects.filter(
        Q(category__isnull=True) | Q(tags__isnull=True),
        status=Post.Status.PUBLISHED,
    ).distinct()

def edited_posts() -> QuerySet[Post]:
    """Return posts that have been edited more than 1 hour after creation."""
    return Post.objects.filter(
        updated_at__gt=F("created_at") + timedelta(hours=1)
    )

def comments_by_post_author() -> QuerySet[Comment]:
    """Return comments where the comment author is the same as the post author."""
    return Comment.objects.filter(
        author=F("post__author")
    )

def comments_before_post() -> QuerySet[Comment]:
    """Return comments that were created before their posts."""
    return Comment.objects.filter(
        created_at__lt=F("post__created_at")
    )

def published_authors_emails() -> list[str]:
    """Return emails of authors who have published posts."""
    return list(
        Post.objects.filter(
            status=Post.Status.PUBLISHED
        ).order_by(
            "author__email"
        ).values_list(
            "author__email",
            flat=True
        ).distinct()
    )

def published_posts_overview() -> list[dict[str, Any]]:
    """Return a list of published posts titles, authors, categories."""
    return list(
        Post.objects.filter(
            status=Post.Status.PUBLISHED
        ).annotate(
            author_email=F("author__email"),
            category_name=Coalesce(
                F("category__name"),
                Value("Uncategorized"),
                )
        ).values(
            "title", 
            "author_email",
            "category_name", 
        )
    )

def posts_stats() -> dict[str, Any]:
    """Return statistics about posts."""
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count(
            "id", 
            filter=Q(status=Post.Status.PUBLISHED),
        ),
        drafts=Count(
            "id",
            filter=Q(status=Post.Status.DRAFT),
        ),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )

def average_comments_per_post() -> float:
    """Return the average number of comments per post."""
    result = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(comment_count=Count("comments"))
        .aggregate(average=Avg("comment_count"))
    )
    return round(result["average"] or 0.0, 2)

def categories_with_post_count() -> QuerySet[Category]:
    """Return categories with their total number of posts."""
    return Category.objects.annotate(
        post_count=Count("posts")
    ).order_by("-post_count", "name")

def categories_with_published_count() -> QuerySet[Category]:
    """Return categories with their number of published posts."""
    return Category.objects.annotate(
        published_count=Count(
            "posts",
            filter=Q(posts__status=Post.Status.PUBLISHED),
        )
    )

def top_authors() -> QuerySet[User]:
    """Return authors ordered by number of published posts."""
    return User.objects.annotate(
        published_count=Count(
            "posts",
            filter=Q(posts__status=Post.Status.PUBLISHED),
        )
    ).order_by("-published_count")[:5]

def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Return tags used in at least min_posts posts."""
    return Tag.objects.annotate(
        post_count=Count("posts")
    ).filter(post_count__gte=min_posts)

def posts_per_status() -> list[dict[str, Any]]:
    """Return a list of post counts grouped by status."""
    return list(
        Post.objects.values("status").annotate(
            count=Count("id")
        ).order_by("status")
    )

def users_activity() -> QuerySet[User]:
    """Return users with their number of posts and comments."""
    return User.objects.annotate(
        posts_count=Count("posts", distinct=True),
        comments_count=Count("comments", distinct=True),
    )

HOT_COMMENTS_THRESHOLD = 10
NORMAL_COMMENTS_THRESHOLD = 3

def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Return users whose full name contains the given text."""
    return User.objects.annotate(
        full_name=Concat(
            ("first_name"),
            Value(" "),
            ("last_name"),
        )
    ).filter(full_name__icontains=text)

def published_posts_per_month() -> list[dict[str, Any]]:
    """Return a list of published posts counts grouped by month."""
    return list(
        Post.objects.filter(
            status=Post.Status.PUBLISHED
        ).annotate(
            month=TruncMonth("created_at")
        ).values("month").annotate(
            count=Count("id")
        ).order_by("month")
    )

def posts_with_popularity() -> QuerySet[Post]:
    """Return posts as hot, bormal and quiet by comment count."""
    return Post.objects.annotate(
        comment_count=Count("comments"),
    ).annotate(
        popularity=Case(
            When(
                comment_count__gte=HOT_COMMENTS_THRESHOLD, 
                then=Value("hot"),
            ),
            When(
                comment_count__gte=NORMAL_COMMENTS_THRESHOLD, 
                then=Value("normal"),
            ),
            default=Value("quiet"),
            output_field=CharField(),
        )
    )

def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Get or create a tag by name."""
    slug = slugify(name)
    return Tag.objects.get_or_create(
        slug=slug,
        defaults={"name": name},
    ) 

def publish_old_drafts(days: int) -> int:
    """Publish drafts older than the given number of days."""
    cutoff = timezone.now() - timedelta(days=days)
    return Post.objects.filter(
        status=Post.Status.DRAFT,
        created_at__lt=cutoff,
    ).update(
        status=Post.Status.PUBLISHED,
        updated_at=timezone.now(),
    )

def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add a tag to every post in a category without duplicates."""
    tag = Tag.objects.get(slug=tag_slug)
    post_ids = list(
        Post.objects.filter(
            category__slug=category_slug,
        ).values_list("id", flat=True)
    )

    through_model = Post.tags.through

    through_model.objects.bulk_create(
        [
            through_model(post_id=post_id, tag_id=tag.id)
            for post_id in post_ids
        ],
        ignore_conflicts=True,
    )

    return len(post_ids)

@transaction.atomic
def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move posts to the target category and delete the source."""
    if source_slug == target_slug:
        return 0

    source = Category.objects.get(slug=source_slug)
    target = Category.objects.get(slug=target_slug)

    moved_count = Post.objects.filter(
        category=source
    ).update(category=target)

    source.delete()
    return moved_count


def delete_inactive_users_comments() -> int:
    """Delete comments written by inactive users."""
    deleted_count, _ = Comment.objects.filter(
        author__is_active=False
    ).delete()

    return deleted_count


FEED_LIMIT = 50
NEWEST_WITH_TAGS_LIMIT = 20


def published_feed() -> list[str]:
    """Return the 50 newest published posts with author and category."""
    posts = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("author", "category")
        .order_by("-created_at")[:FEED_LIMIT]
    )

    return [
        f"{post.title} | {post.author.email} | "
        f"{post.category.name if post.category else 'Uncategorized'}"
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """Return the 20 newest posts with their tags."""
    posts = (
        Post.objects.order_by("-created_at")
        .prefetch_related("tags")[:NEWEST_WITH_TAGS_LIMIT]
    )

    return [
        f"{post.title}: {', '.join(tag.name for tag in post.tags.all())}"
        for post in posts
    ]


def categories_with_published_posts() -> dict[str, list[str]]:
    """Group published post titles by category."""
    published = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).order_by("-created_at")

    categories = Category.objects.prefetch_related(
        Prefetch(
            "posts",
            queryset=published,
            to_attr="published_posts",
        )
    )

    return {
        category.name: [
            post.title for post in category.published_posts
        ]
        for category in categories
    }


def posts_with_last_comment() -> QuerySet[Post]:
    """Return published posts with their latest comment body."""
    latest_comment = (
        Comment.objects.filter(post=OuterRef("pk"))
        .order_by("-created_at")
        .values("body")[:1]
    )

    return Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).annotate(
        last_comment=Subquery(latest_comment)
    )


def posts_with_staff_comments() -> QuerySet[Post]:
    """Return posts that have at least one comment from staff."""
    staff_comments = Comment.objects.filter(
        post=OuterRef("pk"),
        author__is_staff=True,
    )

    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Return users whose newest post is a draft."""
    latest_status = (
        Post.objects.filter(author=OuterRef("pk"))
        .order_by("-created_at")
        .values("status")[:1]
    )

    return User.objects.annotate(
        latest_post_status=Subquery(latest_status)
    ).filter(
        latest_post_status=Post.Status.DRAFT
    )




QUERIES = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
    }
