from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('organizations', views.OrganizationViewSet, basename='organization')

urlpatterns = router.urls
