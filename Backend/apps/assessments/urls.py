from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('assessments', views.AssessmentViewSet, basename='assessment')

urlpatterns = router.urls
