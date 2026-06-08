import json

from django.views.generic import TemplateView, ListView

from core.parsers import apteka911
from core.parsers.apteka911.helper_apteka911 import get_categories_apteka911, update_categories_db, \
    update_all_drugs_apteka911, search_preparaty
from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import CategoryApteka911, DrugApteka911


class BasePageViewApteka911(HTMXTemplateMixin, ListView):
    page_content: tuple[str] = ('pharmacy.html',)
    page_title = 'Аптека 911'

    query = None

    list_categories = []
    list_drugs = []

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_queryset(self):
        self.query = (
                self.request.POST.get('q')
                or self.request.GET.get('q')
        )
        print(self.query)

        return DrugApteka911.objects.filter(productNameNormalized__icontains=self.query.casefold()) if self.query else None

    def get_page_content(self):
        return list(self.page_content)

    def get_list_categories(self):
        obj = CategoryApteka911.objects.all()
        return obj

    def get_list_drugs(self):
        obj = DrugApteka911.objects.all()
        return obj

    def get_data_update_categories(self):
        obj = CategoryApteka911.objects.all().order_by('-update_at').first()
        return obj.update_at if obj else 'Ще немає даних...'

    def get_data_update_drugs(self):
        obj = DrugApteka911.objects.all().order_by('-time_updated').first()
        return obj.time_updated if obj else 'Ще немає даних...'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'current_pharmacy': 'apteka911',
            'page_title': self.page_title,
            'word_search': self.query,
            'date_update_category': self.get_data_update_categories(),
            'date_update_drugs': self.get_data_update_drugs(),
            'page_content': self.get_page_content(),
            'table': {
                'table_titles': None,
                'table_content': DrugApteka911.objects.all().values()[:5],
            }
        })
        return ctx


class UpdateCategoryViewApteka911(HTMXTemplateMixin, ListView):
    model = CategoryApteka911

    def update_categories(self):
        categories = get_categories_apteka911()
        update_categories_db(categories)
        return self.model.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        list_categories = self.update_categories()
        date_update_category = list_categories.order_by('-update_at').first()
        ctx.update({
            'date_update_category': date_update_category.update_at if date_update_category else 'Ще немає даних...',
            'table': {
                'table_titles': None,
                'table_content': list_categories,
            }
        })
        return ctx


class UpdateAllDrugsViewApteka911(HTMXTemplateMixin, ListView):
    model = DrugApteka911

    def update_drugs(self):
        # drugs = DrugApteka911.objects.all()
        # for drug in drugs:
        #     drug.productNameNormalized = drug.productName.casefold()
        #
        # DrugApteka911.objects.bulk_update(
        #     drugs,
        #     ['productNameNormalized']
        # )
        url_categories = CategoryApteka911.objects.values_list('pk', 'url')
        update_all_drugs_apteka911(url_categories)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx.update({
            'date_update_drugs': 'updated',
            'table': {
                'table_titles': None,
                'table_content': self.update_drugs(),
            }
        })

        return ctx


class SearchViewApteka911(HTMXTemplateMixin, ListView):
    page_content = ('block_table.html',)

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
                print(f'Знайдено {len(drugs)} препаратів ({drugs[0]['pharmacy']}')

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
            'page_content': self.get_page_content(),

            'table': {
                'name': f'Пошук за "{self.query}"',
                'table_content': ctx['object_list'],
            }
        })

        return ctx
