from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from core.parsers.helper_parser import get_categories_apteka911, save_to_file_categories
from pharmacies.mixins.htmx import HTMXTemplateMixin

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
            'page_title': self.page_title,
            'pharmacy': LIST_PHARMACY,
            'page_content': self.get_page_content(),
        })
        return ctx



