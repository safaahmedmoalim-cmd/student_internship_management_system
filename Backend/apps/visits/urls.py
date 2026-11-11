from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('visits', views.SupervisionVisitViewSet, basename='visit')

urlpatterns = router.urls
