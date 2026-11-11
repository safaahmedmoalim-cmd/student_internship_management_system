from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('supervisors/academic', views.AcademicSupervisorViewSet, basename='academic-supervisor')
router.register('supervisors/industrial', views.IndustrialSupervisorViewSet, basename='industrial-supervisor')
router.register('assignments', views.SupervisorAssignmentViewSet, basename='assignment')

urlpatterns = router.urls
