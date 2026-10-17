from django.http import JsonResponse
from django.views.generic import TemplateView, ListView
from .forms import ReportFilterForm
from .models import Area, Category
from .services import public_reports


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['area_count'] = Area.objects.count()
        ctx['category_count'] = Category.objects.count()
        return ctx


class AreaListView(ListView):
    model = Area
    template_name = 'core/areas.html'
    context_object_name = 'areas'
    paginate_by = 12


class CategoryListView(ListView):
    model = Category
    template_name = 'core/categories.html'
    context_object_name = 'categories'


class MapView(TemplateView):
    template_name = 'core/map.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ReportFilterForm(self.request.GET)
        ctx['filter_form'] = form
        ctx['areas'] = Area.objects.exclude(center_lat__isnull=True).exclude(center_lng__isnull=True)
        return ctx


def map_data(request):
    form = ReportFilterForm(request.GET)
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid filters'}, status=400)
    reports = public_reports(form.cleaned_data)
    if reports is None:
        return JsonResponse({'type': 'FeatureCollection', 'features': []})
    features = []
    for report in reports[:500]:
        if report.latitude is None or report.longitude is None:
            continue
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [float(report.longitude), float(report.latitude)]},
            'properties': {'id': report.pk, 'title': report.title, 'area': report.area.name,
                           'category': report.category.name, 'status': report.get_operational_status_display()},
        })
    return JsonResponse({'type': 'FeatureCollection', 'features': features})
