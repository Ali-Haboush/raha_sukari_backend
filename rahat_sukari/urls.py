# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token # <--- سطر جديد: استيراد الوظيفة مباشرة

from core import views

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

    # هذا المسار الجديد والمعدل لإنشاء وتوليد التوكنات (API للتسجيل والدخول باستخدام التوكن)
    path('api/token/', obtain_auth_token), # <--- تم استبدال الـ include بوظيفة مباشرة
]