"""REST API views."""

import logging

from django.conf import settings
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_permissions import IsReader, RolePermission
from .models import Article, CustomUser, Newsletter, Publisher
from .selectors import approved_articles, subscribed_articles
from .serializers import (
    ArticleSerializer,
    NewsletterSerializer,
    PublisherSerializer,
    UserSerializer,
)

approved_logger = logging.getLogger('news.approved')


class ArticleListCreateView(generics.ListCreateAPIView):
    """GET /api/articles/ (approved) and POST /api/articles/ (journalists)."""

    serializer_class = ArticleSerializer
    permission_classes = [RolePermission]
    model_name = 'article'

    def get_queryset(self):
        user = self.request.user
        wants_pending = self.request.query_params.get('pending') == 'true'
        if wants_pending and user.has_perm('news.approve_article'):
            return Article.objects.filter(approved=False)  # editors' queue
        return approved_articles()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class SubscribedArticleListView(generics.ListAPIView):
    """GET /api/articles/subscribed/ - only the reader's subscriptions."""

    serializer_class = ArticleSerializer
    permission_classes = [IsReader]

    def get_queryset(self):
        return subscribed_articles(self.request.user)


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/articles/<id>/."""

    serializer_class = ArticleSerializer
    permission_classes = [RolePermission]
    model_name = 'article'

    def get_queryset(self):
        user = self.request.user
        queryset = Article.objects.select_related('author', 'publisher')
        if user.role == CustomUser.Role.EDITOR:
            return queryset
        return queryset.filter(Q(approved=True) | Q(author=user))


class NewsletterListCreateView(generics.ListCreateAPIView):
    serializer_class = NewsletterSerializer
    permission_classes = [RolePermission]
    model_name = 'newsletter'
    queryset = Newsletter.objects.select_related('author')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class NewsletterDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NewsletterSerializer
    permission_classes = [RolePermission]
    model_name = 'newsletter'
    queryset = Newsletter.objects.select_related('author')


class PublisherListView(generics.ListAPIView):
    serializer_class = PublisherSerializer
    permission_classes = [IsAuthenticated]
    queryset = Publisher.objects.all()


class MeView(generics.RetrieveAPIView):
    """GET /api/me/ - the logged-in user's profile."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ApprovedArticleLogView(APIView):
    """POST /api/approved/ - the endpoint our approval signal calls.

    It simulates an external partner: it only accepts calls carrying the
    shared internal token and writes the article to approved_articles.log.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if (
            request.headers.get('X-Internal-Token')
            != settings.INTERNAL_API_TOKEN
        ):
            return Response(
                {'detail': 'Invalid internal token.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        approved_logger.info('Approved article: %s', dict(request.data))
        return Response({'status': 'logged'}, status=status.HTTP_201_CREATED)
