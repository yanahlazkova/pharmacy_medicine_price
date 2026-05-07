import json

from django.views.generic import TemplateView, ListView

from core.parsers.apteka911.helper_apteka911 import get_categories_apteka911, update_categories_db, \
    update_drugs_apteka911, save_to_file
from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import CategoryApteka911, DrugApteka911


# class BasePageViewApteka911(TemplateView):
class BasePageViewApteka911(HTMXTemplateMixin, TemplateView):
    page_content: tuple[str] = ('pharmacy.html',)
    page_title = 'Аптека 911'
    date_update_category = None
    list_categories = []
    list_drugs = []

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
            'page_title': self.page_title,
            'date_update_category': self.get_data_update_categories(),
            'date_update_drugs': self.get_data_update_drugs(),
            'page_content': self.get_page_content(),
            'table': {
                'table_titles': None,
                'table_content': CategoryApteka911.objects.all().values(),
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


class UpdateDrugsViewApteka911(HTMXTemplateMixin, ListView):
    model = DrugApteka911

    def update_drugs(self):
        url_categories = CategoryApteka911.objects.values_list('pk', 'url')
        update_drugs_apteka911(url_categories)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # with open('apteka911.json') as f:
        #     file_content = f.read()
        #     preparaty_json = json.loads(file_content)
        #
        #     for drug in preparaty_json:
        #         try:
        #             DrugApteka911.objects.update_or_create(
        #                 productID=drug['productID'],
        #                 defaults={
        #                     'category': drug['category'],
        #                     'productName': drug['productName'],
        #                     'alias': drug['alias'],
        #                     'brandName': drug['brandName'],
        #                     'formName': drug['formName'],
        #                     'productAvail': True if drug['productAvail'] == 'yes' else False,
        #                     'productCountry': drug['productCountry'],
        #                     'productForm': drug['productForm'],
        #                     'productMeasure': drug['productMeasure'],
        #                     'productMname': drug['productMname'],
        #                     'productPrice': drug['productPrice'],
        #                     'img': drug['img'],
        #
        #                     # 'img': f"https://apteka911.ua{drug.get('dataUrl', '')}{drug.get('productThumbs', {}).get('webpmid', {}).get('file', '')}",
        #
        #                 }
        #             )
        #         except Exception as e:
        #             print(f"[DB ERROR]: {e}")
        #
        # print("Updated preparaty")


        ctx.update({
            'date_update_drugs': 'updated',
            'table': {
                'table_titles': None,
                'table_content': self.update_drugs(),
            }
        })

        return ctx


# class PharmacyUpdateCategory(PharmacyBaseView, HTMXTemplateMixin, ToolbarMixin, TemplateView):
#     # page_content = ('pharmacy.html',)
#     queryset = CategoryApteka911.objects.all()
#
#     def get_queryset(self):
#         # отримати категорії зі сторінки сайту
#         categories = get_categories_whith_page_cite_apteka911()
#         update_categories_db(categories)
#         return CategoryApteka911.objects.all()
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         categories = self.get_queryset()
#
#         today = timezone.now().date()
#
#         # ctx.update({
#         #     'update_categories': today.strftime('%Y-%m-%d:%H-%M-%S'),
#         # })
#
#         return ctx


