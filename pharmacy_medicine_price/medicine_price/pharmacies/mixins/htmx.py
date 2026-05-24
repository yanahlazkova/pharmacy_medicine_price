class HTMXTemplateMixin:
    """
    Якщо запит HTMX — повертаємо частковий template (без layout)
    Якщо ні — повну сторінку
    """

    template_name = "base_page.html"
    htmx_template_name = 'htmx_page.html'

    def get_template_names(self):
        if self.request.headers.get("HX-Request") and self.htmx_template_name:
            return [self.htmx_template_name]
        return [self.template_name]