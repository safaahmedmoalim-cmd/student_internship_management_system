from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('logbooks', views.LogbookViewSet, basename='logbook')
router.register('attendance', views.AttendanceViewSet, basename='attendance')

urlpatterns = router.urls
