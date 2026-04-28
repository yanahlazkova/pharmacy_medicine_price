from django.shortcuts import render
from django.views.generic import TemplateView, UpdateView

from pharmacies.mixins.htmx import HTMXTemplateMixin
from pharmacies.models import CategoryApteka911, DrugApteka911


class BasePageViewApteka911(TemplateView):
# class BasePageViewApteka911(HTMXTemplateMixin, TemplateView):
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'page_title': self.page_title,
            'date_update_category': self.date_update_category,
            'page_content': self.get_page_content(),
        })
        return ctx


class UpdateCategoryViewApteka911(UpdateView):
    model = CategoryApteka911

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = CategoryApteka911.objects.all()
        ctx.update({
            'update_category': 'Categories update',
        })
        return ctx
def update_categoriesy_apteka911(request):
    return render(request, 'pharmacy.html', context={
    'update_categories': 'Categories update',
    })
