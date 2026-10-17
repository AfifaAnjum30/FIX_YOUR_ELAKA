from django.contrib import admin
from .models import Area, Category

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'center_lat', 'center_lng')
    search_fields = ('name', 'description')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'requires_after_photo')
    list_filter = ('type', 'requires_after_photo')
    search_fields = ('name', 'description')
