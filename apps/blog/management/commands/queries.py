from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.queries import QUERIES

PREVIEW_LIMIT = 5
WRITE_QUERY_START = 40
WRITE_QUERY_END = 44
WRITE_QUERIES = set(range(WRITE_QUERY_START, WRITE_QUERY_END + 1))

SAMPLE_ARGUMENTS = {
    4: {"slug": None},
    7: {"page": 1},
    8: {"word": "a"},
    9: {"domain": "example.com"},
    11: {"slugs": ["backend-development", "data-science"]},
    12:{"year": timezone.localdate().year, "month": timezone.localdate().month},
    13: {"days": 365},
    14: {"start": timezone.localdate() - timedelta(days=365), "end": timezone.localdate()},
    15: {"email": None},
    16: {"tag_slug": "python"},
    17: {"category_slug": "backend-development"},
    21: {"first_slug": "python", "second_slug": "django"},
    22: {"text": "a"},
    34: {"min_posts": 3},
    37: {"text": "a"},
    40: {"name": "Django ORM"},
    41: {"days": 180},
    42: {
        "category_slug": "backend-development",
        "tag_slug": "python",
    },
    43: {
        "source_slug": "frontend-development",
        "target_slug": "backend-development",
    }
}


class Command(BaseCommand):
    """Run ORM homework queries and display SQL statistics."""

    help = "Run Django ORM homework queries."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--number", type=int)
        parser.add_argument("--sql", action="store_true")

    def get_arguments(self, number: int) -> dict[str, Any]:
        """Return sample arguments for the selected query."""
        arguments = SAMPLE_ARGUMENTS.get(number, {}).copy()

        if number == 4:
            slug = Post.objects.values_list(
                "slug", flat=True
            ).first()
            arguments["slug"] = slug or "missing-post"
        
        if number == 15:
            email = Post.objects.values_list(
                "author__email", flat=True
            ).first()
            arguments["email"] = email or "missing@examlpe.com"

        return arguments

    def run_query(
        self,
        number: int,
        function: Callable[..., Any],
        show_sql: bool,
    ) -> None:
        """Execute a query and display its result."""
        arguments = self.get_arguments(number)

        annotation_names = ()

        with CaptureQueriesContext(connection) as context:
            result = function(**arguments)

            if isinstance(result, QuerySet):
                annotation_names = tuple(result.query.annotations)
                result = list(result)

        count = len(context.captured_queries)
        label = "query" if count == 1 else "queries"

        self.stdout.write(
            f"#{number} {function.__name__} — "
            f"{count} SQL {label}"
        )

        if show_sql:
            for query in context.captured_queries:
                self.stdout.write(query["sql"])

        if isinstance(result, list):
            for item in result[:PREVIEW_LIMIT]:
                if isinstance(item, Model) and annotation_names:
                    details = {
                        name: getattr(item, name)
                        for name in annotation_names
                    }
                    self.stdout.write(f"  {item}: {details}")
                else:
                    self.stdout.write(f"  {item}")

            self.stdout.write(f"  ({len(result)} rows)")
        else:
            self.stdout.write(f"  {result}")

    def handle(self, *args: Any, **options: Any) -> None:
        """Run one query or all read-only queries."""
        number = options["number"]
        show_sql = options["sql"]

        if number is not None:
            if number not in QUERIES:
                raise CommandError(
                    f"Query #{number} does not exist."
                )
            numbers = [number]
        else:
            numbers = [
                key
                for key in sorted(QUERIES)
                if key not in WRITE_QUERIES
            ]

        for query_number in numbers:
            self.run_query(
                query_number,
                QUERIES[query_number],
                show_sql,
            )
