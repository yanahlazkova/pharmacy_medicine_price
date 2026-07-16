from collections import defaultdict
from random import choice

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

# from core.parsers.apteka1sa.helper_1sa import search_preparaty
# from core.parsers.apteka911.helper_apteka911 import search_preparaty
from core.parsers.apteka911 import helper_apteka911 as apteka911
from core.parsers.apteka1sa import helper_1sa as apteka1sa

from core.parsers.apteka_dobrogo_dnya import helper_add as apteka_dobrogo_dnia
from home.models import SearchResult, Filters

from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import DrugApteka911

LIST_PHARMACY = {
    'apteka911': {
        'name': 'Аптека 911',
        'function': apteka911.search_preparaty,
    },
    # 'add': {
    #     'name': 'Аптека доброго дня',
    #     'function': apteka_dobrogo_dnia.search_preparaty,
    # },
    '1sa': {
        'name': 'Перша соціальна аптека',
        'function': apteka1sa.search_preparaty,
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
        list_filters = Filters.objects.filter(session_key=session_key)

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


class SearchView(HTMXTemplateMixin, ListView):
    # template_name = "base_page.html"
    # htmx_template_name = "htmx_page.html"

    page_content = ('pharmacy_filters.html', 'block_table.html', 'filter_panel.html',)

    # context_object_name = 'search_preparaty'

    query = None

    # кількість знайдених препаратів по аптекам
    number_found = None

    def post(self, request, *args, **kwargs):
        # HTMX відправляє POST, але ListView працює через GET.
        # Ми кажемо Django: "Оброби цей POST як звичайний запит списку"
        return self.get(request, *args, **kwargs)

    def get_queryset(self):
        self.number_found = {}

        self.query = (
                self.request.GET.get('q')
                or self.request.POST.get('q')
        )
        selected_pharmacies = self.request.POST.getlist('pharmacies')

        # ключ сесії
        if not self.request.session.session_key:
            self.request.session.create()

        session_key = self.request.session.session_key
        print(f'session_key: {session_key}')

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

                for pharmacy in selected_pharmacies:
                    search_func = LIST_PHARMACY.get(pharmacy).get('function')
                    if search_func:
                        count_drugs, error = search_func(self.request, self.query, session_key)
                        if error:
                            print(f'error: {error}')
                        else:
                            self.number_found[pharmacy] = count_drugs
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

    def get_list_filters(self):
        # ключ сесії
        session_key = self.request.session.session_key

        filters = Filters.objects.filter(session_key=session_key, query=self.query).values("filter_name", "filter_value")
        filters_dict = defaultdict(list)
        for item in filters:
            filters_dict[item["filter_name"]].append(item["filter_value"])

        filters_dict = dict(filters_dict)

        return filters_dict

    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        pharmacy_data = {}

        for key, pharm in LIST_PHARMACY.items():
            pharmacy_data[key] = {
                "name": pharm["name"],
                "function": pharm["function"],
                "count": self.number_found.get(key, 0),
            }

        filters = self.get_list_filters()

        ctx.update({
            'form_search': 'search',
            'page_title': 'Результати пошуку',
            'query': self.query,
            'filters': filters,
            'pharmacy': pharmacy_data,
            'page_content': self.get_page_content(),
            'number_found': self.number_found,
            'table': {
                'name': f'Пошук ліків за "{self.query}"',
                'table_content': ctx['object_list'],
            }
        })

        return ctx


class FilterByFoundView(HTMXTemplateMixin, ListView):
    page_content = ('block_filter.html', 'block_table.html',)

    list_filter = []

    def post(self, request, *args, **kwargs):
        # HTMX відправляє POST, але ListView працює через GET.
        # Ми кажемо Django: "Оброби цей POST як звичайний запит списку"
        return self.get(request, *args, **kwargs)

    def get_queryset(self):
        print(f'method: {self.request.method}')
        filter = self.request.POST.get('filter_query').casefold()
        print(f'filter: {filter}')
        self.list_filter.append(filter)

        # ключ сесії
        if not self.request.session.session_key:
            self.request.session.create()

        session_key = self.request.session.session_key
        return  SearchResult.objects.filter(session_key=session_key, nameNormalized__icontains=filter).order_by('name',
                                                                                                               'price')
    def get_page_content(self):
        return list(self.page_content)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'form_search': 'search',
            'page_content': self.get_page_content(),
            'filter': self.list_filter,
            'table': {
                # 'name': f'Пошук ліків за "{self.query}"',
                'table_content': ctx['object_list'],
            }

        })

        return ctx
