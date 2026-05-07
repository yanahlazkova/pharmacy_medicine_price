from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from core.parsers.apteka911.helper_apteka911 import create_session, fetch_page, parse_category, update_drugs_apteka911
from core.parsers.helper_parser import get_categories_apteka911, save_to_file_categories
from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import DrugApteka911, CategoryApteka911

LIST_PHARMACY = {
    'apteka911': 'Аптека 911',
    'add': 'Аптека доброго дня',
    '1sa': 'Перша соціальна аптека',
}

class HomePageView(HTMXTemplateMixin, TemplateView):
    page_content: tuple[str] = ('home.html',)
    page_title = 'Порівнюй ціни - обирай найкраще'

    template_name = "base_page.html"
    htmx_template_name = 'htmx_page.html'

    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'form_search': 'search',
            'page_title': self.page_title,
            'pharmacy': LIST_PHARMACY,
            'page_content': self.get_page_content(),
        })
        return ctx


class SearchView(HTMXTemplateMixin, ListView):
    model = DrugApteka911
    context_object_name = 'search_preparaty'
    # Вказуємо шаблон для результатів
    # template_name = 'search_results.html'

    def post(self, request, *args, **kwargs):
        # HTMX робить POST запит. Викликаємо метод get,
        # який всередині себе запустить get_queryset
        return self.get(request, *args, **kwargs)

    def get_queryset(self):
        # Отримуємо запит з POST (або з GET для сумісності)
        query = self.request.POST.get('q') or self.request.GET.get('q')
        if query:
            # Використовуємо icontains для пошуку за частиною слова без урахування регістру
            res = self.model.objects.filter(productName__icontains=query)
            for r in res:
                print(f'{r.productName}: {r.category}')
                self.update_category(r.category)
            return self.model.objects.filter(productName__icontains=query)

        return self.model.objects.none()

    def update_category(self, url_category):
        res = CategoryApteka911.objects.filter(name__icontains='Жарознижуючі')
        list_category = [cat.url_category for cat in res]
        update_drugs_apteka911(list_category)
        print(f'name: {res.name}, url_category: {res.url}')



    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'page_title': 'Результати пошуку',
            'query': self.request.POST.get('q', ''),
            'pharmacy': LIST_PHARMACY,
        })
        return ctx