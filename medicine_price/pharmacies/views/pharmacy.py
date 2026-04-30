from django.shortcuts import render
from django.views.generic import TemplateView, UpdateView, ListView

from pharmacies.helper import get_categories_whith_page_cite_apteka911, update_categories_db
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
        categories = get_categories_whith_page_cite_apteka911()
        update_categories_db(categories)
        return self.model.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        list_categories = self.update_categories()
        update_category = list_categories.order_by('-update_at').first()
        ctx.update({
            'update_category': update_category.update_at if update_category else 'Ще немає даних...',
            'table': {
                'table_titles': None,
                'table_content': list_categories.values(),
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


