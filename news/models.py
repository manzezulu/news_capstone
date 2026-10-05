"""Database models for the news application."""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Publisher(models.Model):
    """A curated publication with many editors and many journalists."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='publishers_edited',
        blank=True,
        limit_choices_to={'role': 'editor'},
    )
    journalists = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='publishers_written_for',
        blank=True,
        limit_choices_to={'role': 'journalist'},
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """User with a role and role-specific relations."""

    class Role(models.TextChoices):
        READER = 'reader', 'Reader'
        EDITOR = 'editor', 'Editor'
        JOURNALIST = 'journalist', 'Journalist'

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.READER
    )

    # Reader-only fields
    subscribed_publishers = models.ManyToManyField(
        Publisher, related_name='subscribers', blank=True
    )
    subscribed_journalists = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='journalist_subscribers',
        blank=True,
        limit_choices_to={'role': 'journalist'},
    )

    def save(self, *args, **kwargs):
        """Save, then enforce 'reader fields are empty for non-readers'."""
        super().save(*args, **kwargs)
        if self.role != self.Role.READER:
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()

    # Journalist-only helpers (reverse relations from Article / Newsletter)
    @property
    def independent_articles(self):
        """Articles this journalist published without a publisher."""
        return self.articles.filter(publisher__isnull=True)

    @property
    def independent_newsletters(self):
        """Newsletters this journalist published."""
        return self.newsletters.all()

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class Article(models.Model):
    """A news article, independent (no publisher) or under a publisher."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='articles',
        limit_choices_to={'role': 'journalist'},
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    # Guards against sending the approval email/POST more than once
    notified = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ['-created_at']
        permissions = [('approve_article', 'Can approve articles')]

    @property
    def is_independent(self):
        return self.publisher_id is None

    def clean(self):
        """Validate author role and publisher membership."""
        if self.author_id and self.author.role != CustomUser.Role.JOURNALIST:
            raise ValidationError('Only journalists can author articles.')
        if (
            self.publisher_id
            and self.author_id
            and not self.publisher.journalists.filter(
                pk=self.author_id
            ).exists()
        ):
            raise ValidationError(
                'The author is not a journalist at this publisher.'
            )

    def __str__(self):
        return self.title


class Newsletter(models.Model):
    """A curated collection of articles created by a journalist."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='newsletters',
        limit_choices_to={'role': 'journalist'},
    )
    articles = models.ManyToManyField(
        Article, related_name='newsletters', blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
