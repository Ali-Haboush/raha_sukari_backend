# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

from core.views import (
    UserViewSet, CustomAuthToken, PatientProfileViewSet,
    BloodGlucoseReadingViewSet, MedicationViewSet, DoctorNoteViewSet,
    AttachmentViewSet, ConsultationViewSet, AlertViewSet, # تم إضافة AlertViewSet
    generate_pdf_report
)

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

# إعدادات Router لـ ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'patients', PatientProfileViewSet, basename='patient')
router.register(r'glucose-readings', BloodGlucoseReadingViewSet, basename='glucose-reading')
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'doctor-notes', DoctorNoteViewSet, basename='doctor-note')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'consultations', ConsultationViewSet, basename='consultation')
router.register(r'alerts', AlertViewSet, basename='alert') # تم إضافة هذا السطر الجديد

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', CustomAuthToken.as_view(), name='api_token_auth'),

    path('api/consultations/<int:consultation_id>/generate_pdf/', generate_pdf_report, name='generate-pdf-report'),

    # مسارات Swagger UI
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# إضافة مسارات لخدمة الملفات الثابتة والوسائط في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)