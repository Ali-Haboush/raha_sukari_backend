# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # هذا هو السطر الأهم: يوجه كل طلبات الـ API إلى تطبيق core
    path('api/', include('core.urls')),

    # مسارات drf-spectacular لتوثيق الـ API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]