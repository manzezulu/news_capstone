"""Web routes."""

from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='article-list'), name='home'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('articles/', views.ArticleListView.as_view(), name='article-list'),
    path('articles/mine/', views.MyArticlesView.as_view(), name='my-articles'),
    path(
        'articles/new/',
        views.ArticleCreateView.as_view(),
        name='article-create',
    ),
    path(
        'articles/<int:pk>/',
        views.ArticleDetailView.as_view(),
        name='article-detail',
    ),
    path(
        'articles/<int:pk>/edit/',
        views.ArticleUpdateView.as_view(),
        name='article-update',
    ),
    path(
        'articles/<int:pk>/delete/',
        views.ArticleDeleteView.as_view(),
        name='article-delete',
    ),
    path('review/', views.ReviewQueueView.as_view(), name='review-queue'),
    path(
        'review/<int:pk>/approve/',
        views.approve_article,
        name='article-approve',
    ),
    path(
        'newsletters/',
        views.NewsletterListView.as_view(),
        name='newsletter-list',
    ),
    path(
        'newsletters/new/',
        views.NewsletterCreateView.as_view(),
        name='newsletter-create',
    ),
    path(
        'newsletters/<int:pk>/',
        views.NewsletterDetailView.as_view(),
        name='newsletter-detail',
    ),
    path(
        'newsletters/<int:pk>/edit/',
        views.NewsletterUpdateView.as_view(),
        name='newsletter-update',
    ),
    path(
        'newsletters/<int:pk>/delete/',
        views.NewsletterDeleteView.as_view(),
        name='newsletter-delete',
    ),
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path(
        'subscriptions/<str:kind>/<int:pk>/toggle/',
        views.toggle_subscription,
        name='toggle-subscription',
    ),
]
