"""Admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Article, CustomUser, Newsletter, Publisher


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Show the role and subscriptions on the user form."""

    fieldsets = UserAdmin.fieldsets + (
        (
            'News profile',
            {
                'fields': (
                    'role',
                    'subscribed_publishers',
                    'subscribed_journalists',
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('News profile', {'fields': ('email', 'role')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = UserAdmin.list_filter + ('role',)


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ('editors', 'journalists')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publisher', 'approved', 'created_at')
    list_filter = ('approved', 'publisher')
    actions = ['approve_selected']

    @admin.action(description='Approve selected articles')
    def approve_selected(self, request, queryset):
        """Loop and save so the approval signal fires for each article."""
        for article in queryset.filter(approved=False):
            article.approved = True
            article.save()


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')
    filter_horizontal = ('articles',)
