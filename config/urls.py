from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from accounts.views import admin_login_view

admin.site.site_header = "TINY MARKET 안전 관리"
admin.site.site_title = "TINY MARKET 관리자"
admin.site.index_title = "플랫폼 요소 관리"

urlpatterns = [
    path("accounts/", include("accounts.urls")),
    path("community/", include("community.urls")),
    path("", include("market.urls")),
]

if settings.ENABLE_ADMIN:
    urlpatterns = [
        path("admin/login/", admin_login_view, name="admin_login_throttled"),
        path("admin/", admin.site.urls),
        *urlpatterns,
    ]

handler400 = "config.views.bad_request"
handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
