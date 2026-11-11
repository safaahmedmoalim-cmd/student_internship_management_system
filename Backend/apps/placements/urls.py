from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('placements', views.PlacementViewSet, basename='placement')
router.register('attachment-periods', views.AttachmentPeriodViewSet, basename='attachment-period')

urlpatterns = router.urls
