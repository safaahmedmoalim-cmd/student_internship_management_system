from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({'status': 'ok'})


admin.site.site_header = 'Student Internship and Attachment Management System'
admin.site.site_title = 'Attachment System Admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health),
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.students.urls')),
    path('api/', include('apps.supervisors.urls')),
    path('api/', include('apps.organizations.urls')),
    path('api/', include('apps.placements.urls')),
    path('api/', include('apps.logbooks.urls')),
    path('api/', include('apps.visits.urls')),
    path('api/', include('apps.assessments.urls')),
    path('api/', include('apps.reports.urls')),
    path('api/', include('apps.announcements.urls')),
    path('api/', include('apps.notifications.urls')),
]
