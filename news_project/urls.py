from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'accounts/', include('django.contrib.auth.urls')
    ),  # login, logout, password reset
    path('api/', include('news.api_urls')),
    path('', include('news.urls')),
]
