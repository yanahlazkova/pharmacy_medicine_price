from django.urls import reverse


def get_table_data(self, revers_url, queryset=None):
    if queryset is None:
        queryset = self._model.objects.all().values(*[
            f.name for f in self._model._meta.fields
            if f.name != 'id'
        ])

    included_fields = [f.name for f in self.model._meta.fields if f.name != 'id']

    # Формуємо рядки (table_rows)
    rows_data = []

    for obj in queryset:
        obj.time_created = getattr(obj, 'time_created').strftime("%d.%m.%Y")  # obj['time_created'].strftime("%d.%m.%Y")
        obj.time_updated = getattr(obj, 'time_updated').strftime("%d.%m.%Y")  # obj['time_updated'].strftime("%d.%m.%Y")
        rows_data.append({
            'values': {
                field: getattr(obj, field) for field in included_fields
            },
            # 'values': obj,
            # URL для HTMX
            'row_url': reverse(viewname=revers_url, kwargs={self.slug_url_kwarg: getattr(obj, self.slug_field)}),
            # 'row_url': reverse(viewname='organization:view_ust', kwargs={self.slug_url_kwarg: obj[self.slug_field]}),
            # .isoformat()}),
            'buttons': [
                UIButtons('view')
                .set_url_name(revers_url)
                .set_kwargs({
                    self.slug_url_kwarg: getattr(obj, self.slug_field),# obj[self.slug_field].isoformat()
                }),
            ]
        })

    return rows_data