from django.db import models


class Area(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    TYPE_CHOICES = (
        ('infrastructure', 'Infrastructure'),
        ('public_utilities', 'Public Utilities'),
        ('environment', 'Environment'),
        ('safety', 'Safety Concern'),
    )
    ICONS = {
        'infrastructure': 'bi-cone-striped',
        'public_utilities': 'bi-lightning-charge-fill',
        'environment': 'bi-tree-fill',
        'safety': 'bi-shield-exclamation',
    }

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    requires_after_photo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['type', 'name']
        constraints = [models.UniqueConstraint(fields=['name', 'type'], name='core_unique_category_name_type')]

    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'

    @property
    def icon_class(self):
        """Bootstrap Icons class used for the category icon on cards."""
        return self.ICONS.get(self.type, 'bi-tag-fill')


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name