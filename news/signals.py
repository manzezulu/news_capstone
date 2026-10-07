"""Signal handlers for the news app.

Keeps each user's permission group in step with their role, and
notifies subscribers (by email and by webhook) when an editor approves
an article.
"""

import logging
from smtplib import SMTPException

import requests
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.mail import send_mass_mail
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article, CustomUser

logger = logging.getLogger(__name__)

# Group name -> permission codenames (matches the brief's role table)
ROLE_PERMISSIONS = {
    'Reader': ['view_article', 'view_newsletter'],
    'Editor': [
        'view_article',
        'change_article',
        'delete_article',
        'approve_article',
        'view_newsletter',
        'change_newsletter',
        'delete_newsletter',
    ],
    'Journalist': [
        'add_article',
        'view_article',
        'change_article',
        'delete_article',
        'add_newsletter',
        'view_newsletter',
        'change_newsletter',
        'delete_newsletter',
    ],
}


def create_role_groups(sender, **kwargs):
    """Create the role groups and (re)assign their permissions.

    Connected to the ``post_migrate`` signal, so the groups exist after
    every ``migrate``. Permissions are replaced, not added to, so the
    groups always match ``ROLE_PERMISSIONS``. Codenames that do not
    exist are ignored.

    :param sender: The app config that has just been migrated
    :type sender: django.apps.AppConfig
    :param kwargs: Other signal arguments (not used)
    :returns: Nothing
    :rtype: None
    """
    for group_name, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = Permission.objects.filter(
            content_type__app_label='news', codename__in=codenames
        )
        group.permissions.set(permissions)


@receiver(post_save, sender=CustomUser)
def sync_role_group(sender, instance, raw=False, **kwargs):
    """Keep the user's group in step with their role.

    Removes the user from every role group, then adds the group whose
    name matches the user's current role. Groups that are not role
    groups are left alone. Skipped when fixtures are loaded.

    :param sender: The model class that sent the signal
    :type sender: type
    :param instance: The user that was saved
    :type instance: news.models.CustomUser
    :param raw: ``True`` when the save comes from ``loaddata``,
        defaults to False
    :type raw: bool, optional
    :param kwargs: Other signal arguments (not used)
    :returns: Nothing
    :rtype: None
    """
    if raw:  # loaddata: skip
        return
    instance.groups.remove(*Group.objects.filter(name__in=ROLE_PERMISSIONS))
    group = Group.objects.filter(name=instance.get_role_display()).first()
    if group:
        instance.groups.add(group)


def get_subscriber_emails(article):
    """Emails of readers subscribed to the article's author or publisher.

    Only users with the Reader role and a non-empty email address are
    included. Each address appears once, even if the reader follows
    both the author and the publisher.

    :param article: The article being announced
    :type article: news.models.Article
    :returns: The distinct subscriber email addresses
    :rtype: list
    """
    condition = Q(subscribed_journalists=article.author)
    if article.publisher_id:
        condition |= Q(subscribed_publishers=article.publisher)
    return list(
        CustomUser.objects.filter(condition, role=CustomUser.Role.READER)
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )


def email_subscribers(article):
    """Send the approved article to each subscriber (one email each).

    Mail errors (``SMTPException`` or ``OSError``) are logged and
    swallowed, so a mail outage never blocks the approval.

    :param article: The approved article
    :type article: news.models.Article
    :returns: The number of emails sent, or 0 if there were no
        recipients or sending failed
    :rtype: int
    """
    recipients = get_subscriber_emails(article)
    if not recipients:
        return 0
    subject = f'New article: {article.title}'
    body = f'By {article.author.username}\n\n{article.content}'
    messages = tuple(
        (subject, body, settings.DEFAULT_FROM_EMAIL, [email])
        for email in recipients
    )
    try:
        return send_mass_mail(messages, fail_silently=False)
    except (SMTPException, OSError) as error:
        logger.error('Could not email article %s: %s', article.pk, error)
        return 0


def post_to_approved_api(article):
    """POST the approved article to our own /api/approved/ endpoint.

    Sends the article id, title, content, author username and
    publisher name (or ``None``) as JSON to ``APPROVED_API_URL``,
    authenticated with the ``X-Internal-Token`` header. The request
    times out after 5 seconds. Any request failure, including an HTTP
    error status, is logged as a warning and not raised.

    :param article: The approved article
    :type article: news.models.Article
    :returns: Nothing
    :rtype: None
    """
    payload = {
        'id': article.pk,
        'title': article.title,
        'content': article.content,
        'author': article.author.username,
        'publisher': article.publisher.name if article.publisher else None,
    }
    try:
        response = requests.post(
            settings.APPROVED_API_URL,
            json=payload,
            headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logger.warning('Approved-article POST failed: %s', error)


@receiver(post_save, sender=Article)
def handle_article_approval(sender, instance, raw=False, **kwargs):
    """When an article becomes approved, notify subscribers exactly once.

    Does nothing for fixture loads, unapproved articles, or articles
    that were already notified. Otherwise it emails the subscribers,
    posts to the approved-articles endpoint, and sets ``notified`` to
    ``True`` so later saves do not notify again.

    :param sender: The model class that sent the signal
    :type sender: type
    :param instance: The article that was saved
    :type instance: news.models.Article
    :param raw: ``True`` when the save comes from ``loaddata``,
        defaults to False
    :type raw: bool, optional
    :param kwargs: Other signal arguments (not used)
    :returns: Nothing
    :rtype: None
    """
    if raw or not instance.approved or instance.notified:
        return
    email_subscribers(instance)
    post_to_approved_api(instance)
    # update() (not save()) so we do not re-trigger this same signal
    Article.objects.filter(pk=instance.pk).update(notified=True)
    instance.notified = True