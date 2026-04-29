from django.urls import path

from home import views
from home.views import HomePageView

app_name = 'home'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
]