from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('students', views.StudentViewSet, basename='student')

urlpatterns = router.urls
