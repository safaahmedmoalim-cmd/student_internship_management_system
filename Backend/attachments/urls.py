from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('placements', views.PlacementViewSet, basename='placement')
router.register('logbook', views.LogbookViewSet, basename='logbook')
# basename "final-report" gives the URL name "final-report-download" that the serializer reverses.
router.register('final-reports', views.FinalReportViewSet, basename='final-report')
router.register('visits', views.VisitViewSet, basename='visit')
router.register('assessments', views.AssessmentViewSet, basename='assessment')
router.register('announcements', views.AnnouncementViewSet, basename='announcement')
router.register('students', views.StudentViewSet, basename='student')

urlpatterns = [
    path('meta/', views.meta, name='meta'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reports/summary/', views.ReportSummaryView.as_view(), name='report-summary'),
    path('reports/summary.csv', views.ReportCsvView.as_view(), name='report-summary-csv'),
    path('', include(router.urls)),
]
