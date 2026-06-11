from django.urls import path
from .views import kendra_dashboard

urlpatterns = [

    path(
        "",
        kendra_dashboard,
        name="kendra_dashboard"
    ),

]