import random
import time
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)
from django.db import transaction
from django.utils.text import slugify
from faker import Faker

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500
SEED_PASSWORD = "SeedPassword123!"
INACTIVE_PROBABILITY = 0.15
STAFF_PROBABILITY = 0.05
PUBLISHED_PROBABILITY = 0.70
NO_CATEGORY_PROBABILITY = 0.10
MAX_TAGS_PER_POST = 5
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3
CATEGORY_NAMES = [
    "Backend Development",
    "Frontend Development",
    "Data Science",
    "Artificial Intelligence",
    "Cybersecurity",
    "Cloud Computing",
    "Mobile Development",
    "Software Engineering",
]

TAG_NAMES = [
    "Python",
    "Django",
    "JavaScript",
    "React",
    "HTML",
    "CSS",
    "REST API",
    "PostgreSQL",
    "Docker",
    "AWS",
    "Machine Learning",
    "Deep Learning",
    "Git",
    "GitHub",
    "Linux",
    "Testing",
    "Security",
    "DevOps",
    "FastAPI",
    "Database",
]

class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )

        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )

        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def create_users(self, count: int) -> list[User]:
        fake = Faker()

        used_emails = set(
            User.objects.values_list("email", flat=True)
        )

        password_hash = make_password(SEED_PASSWORD)

        users = []

        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()

            base_email = (
                f"{first_name}.{last_name}"
                .lower()
                .replace(" ", "")
            )

            email = f"{base_email}@example.com"
            suffix = 2

            while email in used_emails:
                email = f"{base_email}{suffix}@example.com"
                suffix += 1

            used_emails.add(email)

            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password_hash,
                is_active=random.random() >= INACTIVE_PROBABILITY,
                is_staff=random.random() < STAFF_PROBABILITY,
            )

            users.append(user)

        return User.objects.bulk_create(users)
    
    def create_categories_and_tags(self) -> tuple[int, int]:
        categories_created = 0
        tags_created = 0

        for name in CATEGORY_NAMES:
            slug = slugify(name)

            _, created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name},
            )

            if created:
                categories_created += 1

        for name in TAG_NAMES:
            slug = slugify(name)

            _, created = Tag.objects.get_or_create(
                slug=slug,
                defaults={"name": name},
            )

            if created:
                tags_created += 1

        return categories_created, tags_created
    
    def create_posts(self, count: int) -> list[Post]:
        if count == 0:
            return []

        fake = Faker()

        users = list(User.objects.all())
        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())

        if not users:
            raise CommandError(
                "Cannot create posts without users."
            )

        used_slugs = set(
            Post.objects.values_list("slug", flat=True)
        )

        posts = []
        post_tags = []

        for _ in range(count):
            title = fake.sentence(nb_words=6).rstrip(".")[:200]

            base_slug = slugify(title)[:45].rstrip("-") or "post"
            slug = base_slug
            suffix = 2

            while slug in used_slugs:
                ending = f"-{suffix}"
                slug = f"{base_slug[:50 - len(ending)]}{ending}"
                suffix += 1

            used_slugs.add(slug)

            author = random.choice(users)

            if random.random() < NO_CATEGORY_PROBABILITY:
                category = None
            else:
                category = random.choice(categories) if categories else None

            if random.random() < PUBLISHED_PROBABILITY:
                status = Post.Status.PUBLISHED
            else:
                status = Post.Status.DRAFT

            post = Post(
                author=author,
                title=title,
                slug=slug,
                body="\n\n".join(fake.paragraphs(nb=4)),                
                category=category,
                status=status,
            )

            posts.append(post)

            selected_tags = random.sample(
                tags,
                k=random.randint(0, min(MAX_TAGS_PER_POST, len(tags))),
            )
            post_tags.append(selected_tags)

        created_posts = Post.objects.bulk_create(posts)

        for post, selected_tags in zip(
            created_posts, post_tags, strict=True
        ):
            post.tags.set(selected_tags)

        return created_posts

    def create_comments(self, count: int) -> list[Comment]:
        if count == 0:
            return []

        fake = Faker()

        users = list(User.objects.all())

        published_posts = list(
            Post.objects.filter(
                status=Post.Status.PUBLISHED
            )
        )

        if not users:
            raise CommandError(
                "Cannot create comments without users."
            )

        if not published_posts:
            raise CommandError(
                "Cannot create comments without published posts."
            )

        comments = []

        for _ in range(count):
            author = random.choice(users)
            post = random.choice(published_posts)

            sentences_count = random.randint(
                MIN_COMMENT_SENTENCES,
                MAX_COMMENT_SENTENCES,
            )

            comment = Comment(
                author=author,
                post=post,
                body=fake.paragraph(
                    nb_sentences=sentences_count
                ),
            )

            comments.append(comment)

        return Comment.objects.bulk_create(comments)

    def clear_data(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()

        User.objects.filter(is_superuser=False).delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Existing seed data cleared. Superusers preserved."
            )
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]
        start_time = time.perf_counter()
        
        if users_count < 0:
            raise CommandError("Number of users cannot be negative.")

        if posts_count < 0:
            raise CommandError("Number of posts cannot be negative.")

        if comments_count < 0:
            raise CommandError("Number of comments cannot be negative.")

        existing_users = User.objects.count()

        if clear:
            existing_users = User.objects.filter(
                is_superuser=True
            ).count()

        if posts_count > 0 and users_count + existing_users == 0:
            raise CommandError(
                "Cannot create posts without users."
            )

        if comments_count > 0 and users_count + existing_users == 0:
            raise CommandError(
                "Cannot create comments without users."
            )

        with transaction.atomic():
            if clear:
                self.clear_data()

            created_users = self.create_users(users_count)

            categories_count, tags_count = (
                self.create_categories_and_tags()
            )

            created_posts = self.create_posts(posts_count)
            created_comments = self.create_comments(comments_count)

        self.stdout.write(
            self.style.SUCCESS(
                f"Users: {len(created_users)} created"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories: {categories_count} created"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Tags: {tags_count} created"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Posts: {len(created_posts)} created"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Comments: {len(created_comments)} created"
            )
        )

        self.stdout.write(
            self.style.SUCCESS("Seed completed successfully!")
        )

        elapsed_time = time.perf_counter() - start_time

        self.stdout.write(
            f"Execution time: {elapsed_time:.2f} seconds"
        )
