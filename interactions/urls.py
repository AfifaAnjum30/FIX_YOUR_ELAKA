from django.urls import path

from . import views

app_name = "interactions"

urlpatterns = [
    path("report/<int:report_id>/comment/", views.add_comment, name="add_comment"),
    path("report/<int:report_id>/vote/", views.toggle_vote, name="toggle_vote"),
]