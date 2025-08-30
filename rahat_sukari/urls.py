# rahat_sukari/urls.py

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
   
    # يخبر جانغو أن كل روابط تطبيقنا تبدأ بكلمة 'api'
    path('api/', include('core.urls')),

    # مسارات drf-spectacular لتوثيق الـ API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# إضافة هذا الجزء لخدمة ملفات Media في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)