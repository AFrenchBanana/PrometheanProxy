"""
URL configuration for promethean_web project.
Main routing configuration for the PrometheanProxy web interface.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin interface
    path("admin/", admin.site.urls),
    # API endpoints
    path("api/", include("api.urls")),
    # C2 Web Interface
    path("", include("c2_interface.urls")),
]

# Development tools
if settings.DEBUG:
    # Debug toolbar
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        path("__reload__/", include("django_browser_reload.urls")),
    ]

    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
