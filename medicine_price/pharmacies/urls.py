from django.urls import path
from unicodedata import category

from pharmacies.views.pharmacy import apteka911

app_name = 'pharmacies'

urlpatterns = [
    path('apteka911/', apteka911, name='apteka911'),
]