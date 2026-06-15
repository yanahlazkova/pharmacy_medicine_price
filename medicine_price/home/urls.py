from django.urls import path

from home import views
from home.views import HomePageView, SearchView, FilterByFoundView  # , SearchByNameView

app_name = 'home'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('search/', SearchView.as_view(), name='search'),
    path('filter/', FilterByFoundView.as_view(), name='filter'),
]