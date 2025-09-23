from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView, DetailView
from django.http import JsonResponse
from django.http import HttpResponse
from django.template.response import TemplateResponse
from .models import Category, Product, Size
from django.db.models import Q



class IndexView(TemplateView):
    template_name = 'main/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_category'] = None
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'main/home_content.html', context)
        return TemplateResponse(request, self.template_name, context)


class CatalogView(TemplateView):
    template_name = 'main/catalog.html'

    FILTER_MAPPING = {
        'color': lambda queryset, value: queryset.filter(color__iexact=value),
        'min_price': lambda queryset, value: queryset.filter(price__gte=value),
        'max_price': lambda queryset, value: queryset.filter(price__lte=value),
        'size': lambda queryset, value: queryset.filter(product_sizes__size__name=value),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = kwargs.get('category_slug')
        categories = Category.objects.all()
        products = Product.objects.all().order_by('-created_at')
        current_category = None

        if category_slug:
            current_category = get_object_or_404(Category, slug=category_slug)
            products = products.filter(category=current_category)

        query = self.request.GET.get('q')
        if query:
            products = products.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

        filter_params = {}
        for param, filter_func in self.FILTER_MAPPING.items():
            value = self.request.GET.get(param)
            if value:
                products = filter_func(products, value)
                filter_params[param] = value
            else:
                filter_params[param] = ''

        filter_params['q'] = query or ''

        context.update({
            'categories': categories,
            'products': products,
            'current_category': category_slug,
            'filter_params': filter_params,
            'sizes': Size.objects.all(),
            'search_query': query or ''
        })

        if self.request.GET.get('show_search') == 'true':
            context['show_search'] = True
        elif self.request.GET.get('reset_search') == 'true':
            context['reset_search'] = True

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if request.headers.get('HX-Request'):
            # HTMX запросы - возвращаем ЧАСТИЧНЫЕ шаблоны
            if request.GET.get('show_filters') == 'true':
                return TemplateResponse(request, 'main/filter_modal.html', context)
            else:
                # Возвращаем только контент БЕЗ наследования
                return TemplateResponse(request, 'main/catalog_content.html', context)
        else:
            # ОБЫЧНЫЕ запросы - возвращаем ПОЛНУЮ страницу
            return TemplateResponse(request, self.template_name, context)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'main/product_detail.html'  # Полный шаблон с base.html
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        context['categories'] = Category.objects.all()
        context['related_products'] = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id)[:4]
        context['current_category'] = product.category.slug
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)

        # Всегда возвращаем полную страницу
        return TemplateResponse(request, self.template_name, context)


def search(request):
    query = request.GET.get('q', '').strip()

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query),
            is_active=True  # Добавляем фильтр по активным товарам
        ).select_related('category')

        print(f"🔍 Search query: '{query}'")
        print(f"📦 Found {products.count()} products")
        for product in products:
            print(f"   - {product.name} (active: {product.is_active})")
    else:
        products = Product.objects.filter(is_active=True)  # Только активные товары
        print("ℹ️  No query, showing all active products")

    context = {
        'products': products,
        'query': query,
        'title': f'Результаты поиска: {query}' if query else 'Все товары'
    }
    return render(request, 'main/search_results.html', context)


def search_suggestions(request):
    try:
        query = request.GET.get('q', '').strip()
        print(f"🔍 Search suggestions query: '{query}'")

        if not query:
            return JsonResponse({'results': []})

        # Ищем товары
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True  # Добавляем фильтр по активным товарам
        )[:5]

        print(f"📦 Found {products.count()} products")

        results = []
        for product in products:
            print(f"   - {product.name} (slug: {product.slug})")

            # Используем main_image из модели Product
            image_url = product.main_image.url if product.main_image else None

            results.append({
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'price': str(product.price),
                'image': image_url  # Используем main_image
            })

        return JsonResponse({'results': results})

    except Exception as e:
        print(f"❌ Search error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'results': []}, status=500)


def terms(request):
    return render(request, 'main/terms.html')


def privacy(request):
    return render(request, 'main/privacy.html')