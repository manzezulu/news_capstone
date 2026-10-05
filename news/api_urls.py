"""API routes, mounted under /api/."""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import api_views

urlpatterns = [
    path('token/', obtain_auth_token, name='api-token'),
    path('me/', api_views.MeView.as_view(), name='api-me'),
    path(
        'publishers/',
        api_views.PublisherListView.as_view(),
        name='api-publishers',
    ),
    # 'subscribed/' must come BEFORE '<int:pk>/'
    path(
        'articles/',
        api_views.ArticleListCreateView.as_view(),
        name='api-article-list',
    ),
    path(
        'articles/subscribed/',
        api_views.SubscribedArticleListView.as_view(),
        name='api-article-subscribed',
    ),
    path(
        'articles/<int:pk>/',
        api_views.ArticleDetailView.as_view(),
        name='api-article-detail',
    ),
    path(
        'newsletters/',
        api_views.NewsletterListCreateView.as_view(),
        name='api-newsletter-list',
    ),
    path(
        'newsletters/<int:pk>/',
        api_views.NewsletterDetailView.as_view(),
        name='api-newsletter-detail',
    ),
    path(
        'approved/',
        api_views.ApprovedArticleLogView.as_view(),
        name='api-approved',
    ),
]
