from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from core.views import HomeView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    # Temporary home page. The `core` app will replace this later.
    # path("", TemplateView.as_view(template_name="home.html"), name="home"),
    # Member 2 Home Page
    path("", HomeView.as_view(), name="home"),
    # Member 2 Other Pages
    path("", include("core.urls")),
    path("reports/", include("reports.urls")),
    path("interactions/", include("interactions.urls")),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)