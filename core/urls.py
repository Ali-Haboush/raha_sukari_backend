# core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    PatientProfileViewSet,
    BloodGlucoseReadingViewSet,
    MedicationViewSet,
    DoctorNoteViewSet,
    AttachmentViewSet,
    ConsultationViewSet,
    AlertViewSet,
    DoctorViewSet,
    AppointmentViewSet,
    NotificationViewSet, 
    CustomAuthToken,
    generate_pdf_report
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'patients', PatientProfileViewSet, basename='patientprofile')
router.register(r'readings', BloodGlucoseReadingViewSet, basename='bloodglucosereading')
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'doctor-notes', DoctorNoteViewSet, basename='doctornote')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'consultations', ConsultationViewSet, basename='consultation')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'notifications', NotificationViewSet, basename='notification') 

urlpatterns = [
    path('', include(router.urls)),
    path('token/auth/', CustomAuthToken.as_view(), name='token_auth'),
    path('consultations/<int:consultation_id>/report/', generate_pdf_report, name='pdf_report'),
]