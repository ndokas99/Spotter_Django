from django.urls import path
from main.views import PlanRouteView

urlpatterns = [
    path('route-api', PlanRouteView.as_view(), name='route-api')
]