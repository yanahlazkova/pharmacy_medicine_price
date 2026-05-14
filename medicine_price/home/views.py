from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from core.parsers.apteka911.helper_apteka911 import update_all_drugs_apteka911, update_drugs_apteka911, search_preparaty
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


# class SearchView(HTMXTemplateMixin, ListView):
#     model = DrugApteka911
#     page_content: tuple[str] = ('home.html',)
#     context_object_name = 'search_preparaty'
#     # Вказуємо шаблон для результатів
#     # template_name = "base_page.html"
#
#     query = None
#
#     def post(self, request, *args, **kwargs):
#         # HTMX робить POST запит. Викликаємо метод get,
#         # який всередині себе запустить get_queryset
#         return self.get(request, *args, **kwargs)
#
#     def get_queryset(self):
#         # Отримуємо запит з POST (або з GET для сумісності)
#         self.query = self.request.POST.get('q') or self.request.GET.get('q')
#         if self.query:
#
#             # drugs = DrugApteka911.objects.filter(productNameNormalized__icontains=self.query)
#
#             drugs = search_preparaty(self.query)
#             if drugs:
#                 print(f'Знайдено {len(drugs)} препаратів')
#                 for drug in drugs[:5]:
#                     print(f'{drug['productName']}: {drug['productPrice']} ({drug['productAvail']})')
#
#             # update_drugs_apteka911(drugs)
#
#             return drugs
#
#         return self.model.objects.none()
#
#     def get_page_content(self):
#         return list(self.page_content)
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#
#         ctx.update({
#             'page_title': 'Результати пошуку',
#             'query': self.request.POST.get('q', ''),
#             'pharmacy': LIST_PHARMACY,
#             'page_content': self.get_page_content(),
#             'table': {
#                 'name': f'Пошук за {self.query}',
#                 'table_content': self.queryset,
#             }
#         })
#         return ctx

class SearchView(HTMXTemplateMixin, ListView):
    template_name = "base_page.html"
    # htmx_template_name = "htmx_page.html"

    # page_content = ('home.html',)

    context_object_name = 'search_preparaty'

    query = None

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_queryset(self):

        self.query = (
            self.request.POST.get('q')
            or self.request.GET.get('q')
        )

        if self.query:

            drugs = search_preparaty(self.query)

            if drugs:
                print(f'Знайдено {len(drugs)} препаратів')

            return drugs

        return []

    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'page_title': 'Результати пошуку',
            'query': self.query,
            'pharmacy': LIST_PHARMACY,
            # 'page_content': self.get_page_content(),

            'table': {
                'name': f'Пошук за "{self.query}"',
                'table_content': ctx['object_list'],
            }
        })

        return ctx