from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('final-reports', views.FinalReportViewSet, basename='final-report')

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('meta/', views.meta, name='meta'),
    path('reports/', views.ReportListView.as_view(), name='report-list'),
    path('reports/<slug:slug>/', views.ReportView.as_view(), name='report'),
    *router.urls,
]
