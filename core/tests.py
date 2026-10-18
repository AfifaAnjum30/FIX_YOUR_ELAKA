from django.test import TestCase
from django.urls import reverse
from .models import Area, Category

class CoreModelTests(TestCase):
    def test_area_string(self):
        self.assertEqual(str(Area.objects.create(name='Dhanmondi')), 'Dhanmondi')

    def test_category_string(self):
        category = Category.objects.create(name='Pothole', type='infrastructure')
        self.assertIn('Pothole', str(category))

class CoreViewTests(TestCase):
    def test_home(self):
        self.assertEqual(self.client.get(reverse('core:home')).status_code, 200)

    def test_areas(self):
        self.assertEqual(self.client.get(reverse('core:areas')).status_code, 200)

    def test_categories(self):
        self.assertEqual(self.client.get(reverse('core:categories')).status_code, 200)

    def test_map(self):
        self.assertEqual(self.client.get(reverse('core:map')).status_code, 200)

    def test_map_data_without_reports_app(self):
        response = self.client.get(reverse('core:map_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['features'], [])
