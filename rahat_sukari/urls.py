# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from core.views import (
    UserViewSet, PatientProfileViewSet, BloodGlucoseReadingViewSet,
    MedicationViewSet, DoctorNoteViewSet, AttachmentViewSet,
    CustomAuthToken, DoctorViewSet, ConsultationViewSet, AlertViewSet,
    generate_pdf_report,
    AppointmentViewSet
)
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# إعدادات Swagger/OpenAPI
schema_view = get_schema_view(
    openapi.Info(
        title="Rahat Sukari API",
        default_version='v1',
        description="API documentation for Rahat Sukari Diabetes Management System",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@rahatsukari.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'patients', PatientProfileViewSet, basename='patient')
router.register(r'readings', BloodGlucoseReadingViewSet, basename='reading')
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'notes', DoctorNoteViewSet, basename='note')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'consultations', ConsultationViewSet, basename='consultation')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', CustomAuthToken.as_view(), name='token'),
    path('api/consultation/<int:consultation_id>/generate_pdf/', generate_pdf_report, name='generate_pdf_report'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)