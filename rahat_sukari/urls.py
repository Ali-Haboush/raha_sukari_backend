# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# استيراد الأشياء الخاصة بـ drf-yasg
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# استيراد View التوكن المخصص بتاعنا
from core.views import ObtainAuthToken # <--- هذا السطر الجديد

from core import views

# إعدادات الـ schema (صفحة التوثيق)
schema_view = get_schema_view(
    openapi.Info(
        title="Rahat Sukari API",
        default_version='v1',
        description="API documentation for Rahat Sukari Diabetes Monitoring Application",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@rahatsukari.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# إنشاء Router لـ DRF
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'patients', views.PatientProfileViewSet)
router.register(r'readings', views.BloodGlucoseReadingViewSet)
router.register(r'medications', views.MedicationViewSet)
router.register(r'doctor_notes', views.DoctorNoteViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # مسار تسجيل الدخول للحصول على التوكن (الآن يستخدم الـ View المخصص بتاعنا)
    path('api/token/', ObtainAuthToken.as_view(), name='obtain-auth-token'), # <--- هذا السطر تم تعديله

    # مسارات التوثيق (Swagger UI)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]