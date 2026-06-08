from django.urls import path
from unicodedata import category

from home.views import SearchView
from pharmacies.views.apteka911 import BasePageViewApteka911, UpdateCategoryViewApteka911, UpdateAllDrugsViewApteka911

app_name = 'pharmacies'

urlpatterns = [
    path('apteka911/', BasePageViewApteka911.as_view(), name='apteka911'),
    path('apteka911/update_categories/', UpdateCategoryViewApteka911.as_view(), name='update_cat_apteka911'),
    path('apteka911/update_drugs/', UpdateAllDrugsViewApteka911.as_view(), name='update_drugs_apteka911'),
    path('apteka911/search/', SearchView.as_view(), name='search'),
]