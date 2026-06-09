from random import choice

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

# from core.parsers.apteka911.helper_apteka911 import search_preparaty
from core.parsers.apteka911 import helper_apteka911 as apteka911
from core.parsers.apteka1sa import helper_1sa as apteka1sa

from core.parsers.apteka_dobrogo_dnya import helper_add as apteka_dobrogo_dnia
from home.models import SearchResult

from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import DrugApteka911

LIST_PHARMACY = {
    'apteka911': {
        'name': 'Аптека 911',
        'function': apteka911.search_preparaty,
    },
    'add': {
        'name': 'Аптека доброго дня',
        'function': apteka_dobrogo_dnia.search_preparaty,
    },
    '1sa': {
        'name': 'Перша соціальна аптека',
        'function': None,
    },
}

class HomePageView(HTMXTemplateMixin, ListView):
    page_content: tuple[str] = ('home.html',)
    page_title = 'Порівнюй ціни - обирай найкраще'

    template_name = "base_page.html"
    htmx_template_name = 'htmx_page.html'

    def get_queryset(self):
        # ключ сесії
        if not self.request.session.session_key:
            self.request.session.create()

        session_key = self.request.session.session_key

        list_search = SearchResult.objects.filter(session_key=session_key).order_by('name', 'price')
        return list_search

    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'form_search': 'search',
            'page_title': self.page_title,
            'pharmacy': LIST_PHARMACY,
            'page_content': self.get_page_content(),
            'table': {
                'table_content': ctx['object_list'],
                }
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
    # template_name = "base_page.html"
    # htmx_template_name = "htmx_page.html"

    page_content = ('block_table.html',)

    # context_object_name = 'search_preparaty'

    query = None

    def post(self, request, *args, **kwargs):
        # HTMX відправляє POST, але ListView працює через GET.
        # Ми кажемо Django: "Оброби цей POST як звичайний запит списку"
        return self.get(request, *args, **kwargs)

    def get_queryset(self):

        self.query = (
                self.request.GET.get('q')
                or self.request.POST.get('q')
        )
        selected_pharmacies = self.request.POST.getlist('pharmacies')

        # ключ сесії
        if not self.request.session.session_key:
            self.request.session.create()

        session_key = self.request.session.session_key

        print('GET:', self.request.GET)
        print('POST:', self.request.POST)
        print('QUERY:', self.query)
        print(f"Обрані аптеки: {selected_pharmacies}")

        if self.query:

            if self.request.method == 'POST':
                """ пошук за введеним пошуковим словом """

                # очистити таблицю перед новим пошуком
                with transaction.atomic():
                    SearchResult.objects.filter(
                        session_key=self.request.session.session_key
                    ).delete()
                # count_drugs_1sa = apteka1sa.search_preparaty(self.query, session_key)
                for pharmacy in selected_pharmacies:
                    search_func = LIST_PHARMACY.get(pharmacy).get('function')
                    if search_func:
                        count_drugs, error = search_func(self.request, self.query, session_key)
                        if error:
                            print(f'error: {error}')
                        else:
                            print(f'Знайдено {count_drugs} препаратів в {LIST_PHARMACY.get(pharmacy).get('name')}')

                    else:
                        print(f'Не опрацьовується: {LIST_PHARMACY.get(pharmacy).get('name')}')

                # list_search.extend(drugs_apteka911)
                # list_search.extend(drugs_add)
                # list_search.sort(key=lambda x: x['productName'])

                # відсортуємо знайдені дані
                list_search = SearchResult.objects.filter(session_key=session_key).order_by('name', 'price')
                return list_search

            if self.request.method == 'GET':
                """ пошук за назвою препарату з таблиці """
                list_search = SearchResult.objects.filter(session_key=session_key,
                                                          nameNormalized__icontains=self.query.casefold()).order_by(
                    'name', 'price')
                return list_search

        return []

    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'form_search': 'search',
            'page_title': 'Результати пошуку',
            'query': self.query,
            'pharmacy': LIST_PHARMACY,
            'page_content': self.get_page_content(),

            'table': {
                'name': f'Пошук ліків за "{self.query}"',
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
