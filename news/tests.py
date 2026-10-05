"""Unit tests for the news application."""

from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Article, Newsletter, Publisher

User = get_user_model()
PASSWORD = 'pass12345!'


class NewsTestBase(APITestCase):
    """Shared fixtures: users, publishers, subscriptions and articles."""

    @classmethod
    def setUpTestData(cls):
        make = User.objects.create_user
        cls.publisher = Publisher.objects.create(name='Daily Planet')
        cls.journalist = make(
            'jane', 'jane@example.com', PASSWORD, role='journalist'
        )
        cls.other_journalist = make(
            'omar', 'omar@example.com', PASSWORD, role='journalist'
        )
        cls.stranger = make(
            'sam', 'sam@example.com', PASSWORD, role='journalist'
        )
        cls.editor = make('edna', 'edna@example.com', PASSWORD, role='editor')
        cls.reader = make('rita', 'rita@example.com', PASSWORD, role='reader')
        cls.other_reader = make(
            'rob', 'rob@example.com', PASSWORD, role='reader'
        )

        cls.publisher.journalists.add(cls.journalist)
        cls.publisher.editors.add(cls.editor)
        cls.reader.subscribed_publishers.add(cls.publisher)
        cls.reader.subscribed_journalists.add(cls.other_journalist)

        # notified=True stops the approval signal firing while seeding data
        seed = {'approved': True, 'notified': True}
        cls.publisher_article = Article.objects.create(
            title='Publisher story',
            content='...',
            author=cls.journalist,
            publisher=cls.publisher,
            **seed
        )
        cls.independent_article = Article.objects.create(
            title='Independent story',
            content='...',
            author=cls.other_journalist,
            **seed
        )
        cls.unsubscribed_article = Article.objects.create(
            title='Not for Rita', content='...', author=cls.stranger, **seed
        )
        cls.pending_article = Article.objects.create(
            title='Pending story',
            content='...',
            author=cls.journalist,
            publisher=cls.publisher,
        )


class RoleAndGroupTests(NewsTestBase):
    def test_user_is_placed_in_group_for_role(self):
        self.assertEqual(
            list(self.journalist.groups.values_list('name', flat=True)),
            ['Journalist'],
        )
        self.assertEqual(
            list(self.reader.groups.values_list('name', flat=True)), ['Reader']
        )

    def test_group_permissions(self):
        self.assertTrue(self.editor.has_perm('news.approve_article'))
        self.assertFalse(self.journalist.has_perm('news.approve_article'))
        self.assertTrue(self.journalist.has_perm('news.add_article'))
        self.assertFalse(self.reader.has_perm('news.add_article'))

    def test_changing_role_clears_reader_fields_and_swaps_group(self):
        self.reader.role = 'journalist'
        self.reader.save()
        self.assertEqual(self.reader.subscribed_publishers.count(), 0)
        self.assertEqual(self.reader.subscribed_journalists.count(), 0)
        self.assertEqual(
            list(self.reader.groups.values_list('name', flat=True)),
            ['Journalist'],
        )


class AuthenticationTests(NewsTestBase):
    def test_token_endpoint_returns_token(self):
        response = self.client.post(
            reverse('api-token'), {'username': 'rita', 'password': PASSWORD}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_token_endpoint_rejects_bad_password(self):
        response = self.client.post(
            reverse('api-token'), {'username': 'rita', 'password': 'wrong'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_request_is_rejected(self):
        response = self.client.get(reverse('api-article-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ArticleApiTests(NewsTestBase):
    def test_list_returns_only_approved_articles(self):
        self.client.force_authenticate(self.reader)
        response = self.client.get(reverse('api-article-list'))
        titles = {item['title'] for item in response.data}
        self.assertNotIn('Pending story', titles)
        self.assertEqual(len(titles), 3)

    def test_reader_only_gets_subscribed_content(self):
        self.client.force_authenticate(self.reader)
        response = self.client.get(reverse('api-article-subscribed'))
        titles = {item['title'] for item in response.data}
        self.assertEqual(titles, {'Publisher story', 'Independent story'})

    def test_subscribed_endpoint_is_forbidden_for_non_readers(self):
        self.client.force_authenticate(self.journalist)
        response = self.client.get(reverse('api-article-subscribed'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reader_with_no_subscriptions_gets_empty_list(self):
        self.client.force_authenticate(self.other_reader)
        response = self.client.get(reverse('api-article-subscribed'))
        self.assertEqual(response.data, [])

    def test_reader_cannot_see_pending_article(self):
        self.client.force_authenticate(self.reader)
        url = reverse('api-article-detail', args=[self.pending_article.pk])
        self.assertEqual(
            self.client.get(url).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_journalist_can_create_article(self):
        self.client.force_authenticate(self.journalist)
        response = self.client.post(
            reverse('api-article-list'),
            {
                'title': 'New',
                'content': 'Body',
                'publisher': self.publisher.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        article = Article.objects.get(pk=response.data['id'])
        self.assertEqual(article.author, self.journalist)
        self.assertFalse(article.approved)

    def test_reader_cannot_create_article(self):
        self.client.force_authenticate(self.reader)
        response = self.client.post(
            reverse('api-article-list'),
            {'title': 'Nope', 'content': 'Body'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journalist_cannot_publish_under_foreign_publisher(self):
        other = Publisher.objects.create(name='Other Press')
        self.client.force_authenticate(self.journalist)
        response = self.client.post(
            reverse('api-article-list'),
            {'title': 'X', 'content': 'Y', 'publisher': other.pk},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_cannot_self_approve(self):
        self.client.force_authenticate(self.journalist)
        response = self.client.post(
            reverse('api-article-list'),
            {'title': 'X', 'content': 'Y', 'approved': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_cannot_edit_someone_elses_article(self):
        self.client.force_authenticate(self.journalist)
        url = reverse('api-article-detail', args=[self.independent_article.pk])
        response = self.client.put(
            url, {'title': 'Hacked', 'content': 'x'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('news.signals.send_mass_mail')
    @patch('news.signals.requests.post')
    def test_editor_can_approve_via_api(self, mock_post, mock_mail):
        self.client.force_authenticate(self.editor)
        url = reverse('api-article-detail', args=[self.pending_article.pk])
        response = self.client.put(
            url,
            {
                'title': 'Pending story',
                'content': '...',
                'approved': True,
                'publisher': self.publisher.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_article.refresh_from_db()
        self.assertTrue(self.pending_article.approved)

    def test_editor_can_delete_article(self):
        self.client.force_authenticate(self.editor)
        url = reverse('api-article-detail', args=[self.pending_article.pk])
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT
        )
        self.assertFalse(
            Article.objects.filter(pk=self.pending_article.pk).exists()
        )

    def test_reader_cannot_delete_article(self):
        self.client.force_authenticate(self.reader)
        url = reverse('api-article-detail', args=[self.publisher_article.pk])
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN
        )


class NewsletterTests(NewsTestBase):
    def test_newsletter_links_many_articles(self):
        newsletter = Newsletter.objects.create(
            title='Weekly', author=self.journalist
        )
        newsletter.articles.add(
            self.publisher_article, self.independent_article
        )
        self.assertEqual(newsletter.articles.count(), 2)
        self.assertIn(newsletter, self.journalist.independent_newsletters)

    def test_journalist_can_create_newsletter_via_api(self):
        self.client.force_authenticate(self.journalist)
        response = self.client.post(
            reverse('api-newsletter-list'),
            {
                'title': 'Digest',
                'description': 'Best of',
                'articles': [self.publisher_article.pk],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.journalist.pk)

    def test_reader_can_view_but_not_create_newsletters(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(
            self.client.get(reverse('api-newsletter-list')).status_code,
            status.HTTP_200_OK,
        )
        response = self.client.post(
            reverse('api-newsletter-list'), {'title': 'No'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ApprovalSignalTests(NewsTestBase):
    """The signal must email subscribers and POST to /api/approved/ once."""

    def approve(self, article):
        article.approved = True
        article.save()

    @patch('news.signals.send_mass_mail')
    @patch('news.signals.requests.post')
    def test_approval_emails_only_subscribers_and_posts_to_api(
        self, mock_post, mock_mail
    ):
        self.approve(
            self.pending_article
        )  # jane @ Daily Planet; rita subscribes

        recipients = [msg[3][0] for msg in mock_mail.call_args[0][0]]
        self.assertEqual(recipients, ['rita@example.com'])
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['title'], 'Pending story')

    @patch('news.signals.send_mass_mail')
    @patch('news.signals.requests.post')
    def test_unapproved_article_triggers_nothing(self, mock_post, mock_mail):
        self.pending_article.title = 'Edited'
        self.pending_article.save()
        mock_mail.assert_not_called()
        mock_post.assert_not_called()

    @patch('news.signals.send_mass_mail')
    @patch('news.signals.requests.post')
    def test_notification_is_sent_only_once(self, mock_post, mock_mail):
        self.approve(self.pending_article)
        self.pending_article.title = 'Edited later'
        self.pending_article.save()
        self.assertEqual(mock_mail.call_count, 1)
        self.assertEqual(mock_post.call_count, 1)

    @patch('news.signals.send_mass_mail')
    @patch('news.signals.requests.post')
    def test_api_failure_does_not_break_approval(self, mock_post, mock_mail):
        mock_post.side_effect = requests.RequestException('service down')
        self.approve(self.pending_article)  # must not raise
        self.pending_article.refresh_from_db()
        self.assertTrue(self.pending_article.approved)
        mock_mail.assert_called_once()


class WebViewAccessTests(NewsTestBase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('article-list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_reader_cannot_open_review_queue(self):
        self.client.force_login(self.reader)
        self.assertEqual(
            self.client.get(reverse('review-queue')).status_code, 403
        )

    @patch('news.signals.send_mass_mail')
    @patch('news.signals.requests.post')
    def test_editor_can_approve_from_review_queue(self, mock_post, mock_mail):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse('article-approve', args=[self.pending_article.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.pending_article.refresh_from_db()
        self.assertTrue(self.pending_article.approved)

    def test_journalist_cannot_approve(self):
        self.client.force_login(self.journalist)
        response = self.client.post(
            reverse('article-approve', args=[self.pending_article.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_reader_can_subscribe_and_unsubscribe(self):
        self.client.force_login(self.other_reader)
        url = reverse(
            'toggle-subscription', args=['publisher', self.publisher.pk]
        )
        self.client.post(url)
        self.assertIn(
            self.publisher, self.other_reader.subscribed_publishers.all()
        )
        self.client.post(url)
        self.assertNotIn(
            self.publisher, self.other_reader.subscribed_publishers.all()
        )
