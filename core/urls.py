from django.urls import path
from . import views

app_name = 'core'
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('areas/', views.AreaListView.as_view(), name='areas'),
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    path('map/', views.MapView.as_view(), name='map'),
    path('map/data/', views.map_data, name='map_data'),

]
