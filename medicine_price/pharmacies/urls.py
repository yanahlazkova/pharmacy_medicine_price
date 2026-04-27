from django.urls import path
from unicodedata import category

from pharmacies.views.pharmacy import update_categoriesy_apteka911, BasePageViewApteka911

app_name = 'pharmacies'

urlpatterns = [
    path('apteka911/', BasePageViewApteka911.as_view(), name='apteka911'),
    path('apteka911/update_categories/', update_categoriesy_apteka911, name='update_categories_apteka911'),
]