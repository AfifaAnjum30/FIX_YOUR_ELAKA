from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="list"),
    path("new/", views.ReportCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ReportDetailView.as_view(), name="detail"),
    path('<int:report_id>/verify/',views.verify_report,name='verify-report'),
    path('<int:report_id>/update-status/',views.update_report_status,name='update-report-status'),
]