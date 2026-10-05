"""Reusable article queries."""

from django.db.models import Q

from .models import Article


def approved_articles():
    """All approved articles with related rows pre-loaded."""
    return Article.objects.filter(approved=True).select_related(
        'author', 'publisher'
    )


def subscribed_articles(user):
    """Approved articles from the user's subscribed journalists/publishers."""
    return (
        approved_articles()
        .filter(
            Q(author__in=user.subscribed_journalists.all())
            | Q(publisher__in=user.subscribed_publishers.all())
        )
        .distinct()
    )
