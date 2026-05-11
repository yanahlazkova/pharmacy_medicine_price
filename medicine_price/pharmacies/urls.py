from django.urls import path
from unicodedata import category

from pharmacies.views.pharmacy import BasePageViewApteka911, UpdateCategoryViewApteka911, UpdateAllDrugsViewApteka911

app_name = 'pharmacies'

urlpatterns = [
    path('apteka911/', BasePageViewApteka911.as_view(), name='apteka911'),
    path('apteka911/update_categories/', UpdateCategoryViewApteka911.as_view(), name='update_cat_apteka911'),
    path('apteka911/update_drugs/', UpdateAllDrugsViewApteka911.as_view(), name='update_drugs_apteka911'),
]