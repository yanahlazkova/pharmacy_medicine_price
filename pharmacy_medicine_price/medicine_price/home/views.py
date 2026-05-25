from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

# from core.parsers.apteka911.helper_apteka911 import search_preparaty
from core.parsers.apteka911 import helper_apteka911 as apteka911

from core.parsers.apteka_dobrogo_dnya import helper_add as apteka_dobrogo_dnia

from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import DrugApteka911

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
    htmx_template_name = "htmx_page.html"

    page_content = ('block_table.html',)

    # context_object_name = 'search_preparaty'

    query = None

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_queryset(self):
        list_search = []

        self.query = (
            self.request.GET.get('q')
            or self.request.POST.get('q')
        )
        print('GET:', self.request.GET)
        print('POST:', self.request.POST)
        print('QUERY:', self.query)
        if self.query:

            drugs_apteka911 = apteka911.search_preparaty(self.query)
            # drugs_db = DrugApteka911.objects.filter(productNameNormalized__icontains=self.query.casefold(), productAvail=True)
            drugs_add = apteka_dobrogo_dnia.search_preparaty(self.query)

            if drugs_apteka911:

                print(f'Знайдено {len(drugs_apteka911)} препаратів {drugs_apteka911[0]['pharmacy']}')


            if drugs_add:
                print(f'Знайдено {len(drugs_add)} препаратів')

            list_search.extend(drugs_apteka911)
            list_search.extend(drugs_add)
            list_search.sort(key=lambda x: x['productName'])
            return list_search

        return []

    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'page_title': 'Результати пошуку',
            'query': self.query,
            'pharmacy': LIST_PHARMACY,
            'page_content': self.get_page_content(),

            'table': {
                'name': f'Пошук за "{self.query}"',
                'table_content': ctx['object_list'],
            }
        })

        return ctx


# class SearchByNameView(HTMXTemplateMixin, ListView):
#     page_content = ('block_table.html',)
#
#     context_object_name = 'search_preparaty'
#
#     query = None
#
#     def get_queryset(self):
#         list_search = []
#
#         self.query = (
#                 self.request.POST.get('q')
#                 or self.request.GET.get('q')
#         )
#
#         if self.query:
#
#             drugs_apteka911 = apteka911.search_preparaty(self.query)
#             # drugs_db = DrugApteka911.objects.filter(productNameNormalized__icontains=self.query.casefold(), productAvail=True)
#             drugs_add = apteka_dobrogo_dnia.search_preparaty(self.query)
#
#             if drugs_apteka911:
#                 print(f'Знайдено {len(drugs_apteka911)} препаратів')
#
#             if drugs_add:
#                 print(f'Знайдено {len(drugs_add)} препаратів')
#
#             list_search.extend(drugs_apteka911)
#             list_search.extend(drugs_add)
#             list_search.sort(key=lambda x: x['productName'])
#             return list_search
#
#         return []
#
#     def get_page_content(self):
#         return list(self.page_content)
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#
#         ctx.update({
#             'page_title': 'Результати пошуку',
#             'query': self.query,
#             'pharmacy': LIST_PHARMACY,
#             'page_content': self.get_page_content(),
#
#             'table': {
#                 'name': f'Пошук за "{self.query}"',
#                 'table_content': ctx['object_list'],
#             }
#         })
#
#         return ctx