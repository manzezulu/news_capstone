"""Web views for the news application."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import ArticleForm, NewsletterForm, RegistrationForm
from .models import Article, CustomUser, Newsletter, Publisher
from .selectors import approved_articles, subscribed_articles


class OwnerOrEditorMixin:
    """Editors reach every object; journalists only their own."""

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == CustomUser.Role.EDITOR:
            return queryset
        return queryset.filter(author=self.request.user)


# ---------- Accounts ----------
class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')


# ---------- Articles ----------
class ArticleListView(LoginRequiredMixin, ListView):
    template_name = 'news/article_list.html'
    context_object_name = 'articles'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        wants_feed = self.request.GET.get('feed') == 'subscribed'
        if wants_feed and user.role == CustomUser.Role.READER:
            return subscribed_articles(user)
        return approved_articles()


class MyArticlesView(PermissionRequiredMixin, ListView):
    permission_required = 'news.add_article'  # journalists only
    template_name = 'news/article_list.html'
    context_object_name = 'articles'

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user)


class ArticleDetailView(LoginRequiredMixin, DetailView):
    model = Article
    template_name = 'news/article_detail.html'

    def get_queryset(self):
        queryset = Article.objects.select_related('author', 'publisher')
        if self.request.user.role == CustomUser.Role.EDITOR:
            return queryset
        return queryset.filter(Q(approved=True) | Q(author=self.request.user))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related_articles'] = (
            Article.objects.filter(
                author=self.object.author,
                approved=True,
            )
            .exclude(pk=self.object.pk)
            .select_related('author', 'publisher')[:2]
        )
        return ctx


class ArticleCreateView(PermissionRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    permission_required = 'news.add_article'
    template_name = 'news/form.html'
    success_url = reverse_lazy('my-articles')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user  # never trust client input
        messages.success(self.request, 'Article submitted for review.')
        return super().form_valid(form)


class ArticleUpdateView(
    PermissionRequiredMixin, OwnerOrEditorMixin, UpdateView
):
    model = Article
    form_class = ArticleForm
    permission_required = 'news.change_article'
    template_name = 'news/form.html'
    success_url = reverse_lazy('article-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ArticleDeleteView(
    PermissionRequiredMixin, OwnerOrEditorMixin, DeleteView
):
    model = Article
    permission_required = 'news.delete_article'
    template_name = 'news/confirm_delete.html'
    success_url = reverse_lazy('article-list')


# ---------- Editor review ----------
class ReviewQueueView(PermissionRequiredMixin, ListView):
    permission_required = 'news.approve_article'  # editors only
    template_name = 'news/review_queue.html'
    context_object_name = 'articles'

    def get_queryset(self):
        return Article.objects.filter(approved=False).select_related(
            'author', 'publisher'
        )


@login_required
@permission_required('news.approve_article', raise_exception=True)
@require_POST
def approve_article(request, pk):
    """Approve an article; the post_save signal emails and POSTs it."""
    article = get_object_or_404(Article, pk=pk)
    if article.approved:
        messages.info(request, 'That article was already approved.')
    else:
        article.approved = True
        article.save()
        messages.success(request, f'"{article.title}" approved and sent out.')
    return redirect('review-queue')


# ---------- Newsletters ----------
class NewsletterListView(PermissionRequiredMixin, ListView):
    model = Newsletter
    permission_required = 'news.view_newsletter'
    template_name = 'news/newsletter_list.html'
    context_object_name = 'newsletters'


class NewsletterDetailView(PermissionRequiredMixin, DetailView):
    model = Newsletter
    permission_required = 'news.view_newsletter'
    template_name = 'news/newsletter_detail.html'


class NewsletterCreateView(PermissionRequiredMixin, CreateView):
    model = Newsletter
    form_class = NewsletterForm
    permission_required = 'news.add_newsletter'
    template_name = 'news/form.html'
    success_url = reverse_lazy('newsletter-list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class NewsletterUpdateView(
    PermissionRequiredMixin, OwnerOrEditorMixin, UpdateView
):
    model = Newsletter
    form_class = NewsletterForm
    permission_required = 'news.change_newsletter'
    template_name = 'news/form.html'
    success_url = reverse_lazy('newsletter-list')


class NewsletterDeleteView(
    PermissionRequiredMixin, OwnerOrEditorMixin, DeleteView
):
    model = Newsletter
    permission_required = 'news.delete_newsletter'
    template_name = 'news/confirm_delete.html'
    success_url = reverse_lazy('newsletter-list')


# ---------- Subscriptions (readers) ----------
@login_required
def subscriptions(request):
    """List publishers/journalists with subscribe/unsubscribe buttons."""
    if request.user.role != CustomUser.Role.READER:
        raise PermissionDenied
    context = {
        'publishers': Publisher.objects.all(),
        'journalists': CustomUser.objects.filter(
            role=CustomUser.Role.JOURNALIST
        ),
        'my_publisher_ids': set(
            request.user.subscribed_publishers.values_list('pk', flat=True)
        ),
        'my_journalist_ids': set(
            request.user.subscribed_journalists.values_list('pk', flat=True)
        ),
    }
    return render(request, 'news/subscriptions.html', context)


@login_required
@require_POST
def toggle_subscription(request, kind, pk):
    """Subscribe if not subscribed, otherwise unsubscribe."""
    if request.user.role != CustomUser.Role.READER:
        raise PermissionDenied
    if kind == 'publisher':
        target = get_object_or_404(Publisher, pk=pk)
        relation = request.user.subscribed_publishers
    elif kind == 'journalist':
        target = get_object_or_404(
            CustomUser, pk=pk, role=CustomUser.Role.JOURNALIST
        )
        relation = request.user.subscribed_journalists
    else:
        raise Http404('Unknown subscription type.')

    if relation.filter(pk=target.pk).exists():
        relation.remove(target)
        messages.info(request, f'Unsubscribed from {target}.')
    else:
        relation.add(target)
        messages.success(request, f'Subscribed to {target}.')
    return redirect('subscriptions')
