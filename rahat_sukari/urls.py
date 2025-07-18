# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# استيراد الأشياء الخاصة بـ drf-yasg
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework.authtoken.views import obtain_auth_token # عشان API التوكن

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
    permission_classes=(permissions.AllowAny,), # للسماح لأي أحد بالوصول لصفحة التوثيق
)


# إنشاء Router لـ DRF
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'patients', views.PatientProfileViewSet)
router.register(r'readings', views.BloodGlucoseReadingViewSet)
router.register(r'medications', views.MedicationViewSet)
router.register(r'doctor_notes', views.DoctorNoteViewSet)

urlpatterns = [
    path('admin/', admin.site.urls), # مسار لوحة الإدارة
    path('api/', include(router.urls)), # تضمين جميع مسارات الـ APIs التي أنشأها الـ Router تحت '/api/'
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), # مسارات تسجيل الدخول/الخروج الافتراضية لـ DRF

    # مسار خاص لتوليد التوكنات (API للتسجيل والدخول باستخدام التوكن)
    path('api/token/', obtain_auth_token), # هذا المسار الضروري اللي عدلناه سابقا

    # مسارات التوثيق (Swagger UI) - هذا هو الجديد والمهم
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'), # هذا هو رابط ملف الـ JSON اللي Postman بيفهمه
]