# core/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML, CSS
from django.utils import timezone
import os

# استيرادات جديدة للديكورات (Decorators)
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication


from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote, Attachment, Consultation, User
from .serializers import (
    UserSerializer, PatientProfileSerializer, BloodGlucoseReadingSerializer,
    MedicationSerializer, DoctorNoteSerializer, AttachmentSerializer,
    AuthTokenSerializer, DoctorPatientListSerializer, DoctorPatientDetailSerializer,
    ConsultationSerializer
)
from .permissions import IsDoctor, IsPatientOwner, IsOwnerOrDoctor, IsPatientOwnerOrDoctor

# --- User ViewSet ---
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.none()

# --- Custom Auth Token View ---
class CustomAuthToken(ObtainAuthToken):
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        user_type = None
        if hasattr(user, 'patientprofile'):
            user_type = 'patient'
        elif user.is_staff:
            user_type = 'doctor'

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user_type
        })

# --- PatientProfile ViewSet ---
class PatientProfileViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated, IsPatientOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, 'patientprofile'):
                return PatientProfile.objects.filter(user=user)
            elif user.is_staff:
                return PatientProfile.objects.all()
        return PatientProfile.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# --- BloodGlucoseReading ViewSet (تم تصحيح اسم الـ Serializer) ---
class BloodGlucoseReadingViewSet(viewsets.ModelViewSet):
    queryset = BloodGlucoseReading.objects.all()
    serializer_class = BloodGlucoseReadingSerializer # <--- تم تصحيح هذا السطر
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, 'patientprofile'):
                return BloodGlucoseReading.objects.filter(patient=user.patientprofile).order_by('-reading_timestamp')
            elif user.is_staff:
                return BloodGlucoseReading.objects.all().order_by('-reading_timestamp')
        return BloodGlucoseReading.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can create blood glucose readings.")

# --- Medication ViewSet ---
class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, 'patientprofile'):
                return Medication.objects.filter(patient=user.patientprofile).order_by('-start_date')
            elif user.is_staff:
                return Medication.objects.all().order_by('-start_date')
        return Medication.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can add medications.")

# --- DoctorNote ViewSet ---
class DoctorNoteViewSet(viewsets.ModelViewSet):
    queryset = DoctorNote.objects.all()
    serializer_class = DoctorNoteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, 'patientprofile'):
                return DoctorNote.objects.filter(patient=user.patientprofile).order_by('-timestamp')
            elif user.is_staff:
                return DoctorNote.objects.all().order_by('-timestamp')
        return DoctorNote.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save(doctor=self.request.user)
        else:
            raise serializers.ValidationError("Only doctors can create doctor notes.")

# --- Attachment ViewSet ---
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, 'patientprofile'):
                return Attachment.objects.filter(patient=user.patientprofile).order_by('-uploaded_at')
            elif user.is_staff:
                return Attachment.objects.all().order_by('-uploaded_at')
        return Attachment.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can upload attachments.")

# --- Consultation ViewSet ---
class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated, IsPatientOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, 'patientprofile'):
                return Consultation.objects.filter(patient=user.patientprofile).order_by('-consultation_date', '-consultation_time')
            elif user.is_staff:
                return Consultation.objects.all().order_by('-consultation_date', '-consultation_time')
        return Consultation.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save(doctor=self.request.user)
        else:
            raise serializers.ValidationError("Only doctors can create consultations.")

    def perform_update(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
        else:
            raise serializers.ValidationError("Only doctors can update consultations.")

    def perform_destroy(self, instance):
        if self.request.user.is_staff:
            instance.delete()
        else:
            raise serializers.ValidationError("Only doctors can delete consultations.")

# --- PDF Report View ---
@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsDoctor | IsPatientOwnerOrDoctor])
def generate_pdf_report(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)

    user = request.user
    if not user.is_authenticated:
        return HttpResponse("غير مصرح لك بالدخول. يرجى تسجيل الدخول.", status=status.HTTP_401_UNAUTHORIZED)

    if hasattr(user, 'patientprofile') and user.patientprofile != consultation.patient:
        return HttpResponse("غير مصرح لك بالوصول لهذا التقرير.", status=status.HTTP_403_FORBIDDEN)

    if user.is_staff and user != consultation.doctor:
        pass 

    context = {
        'consultation': consultation,
        'patient': consultation.patient,
        'doctor': consultation.doctor,
        'now': timezone.now(),
    }

    html_string = render_to_string('core/consultation_report.html', context)
    html = HTML(string=html_string)

    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="consultation_report_{consultation.id}.pdf"'
    return response

# View لتسجيل الدخول بالبريد الإلكتروني أو اسم المستخدم
class CustomAuthToken(ObtainAuthToken):
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        user_type = None
        if hasattr(user, 'patientprofile'):
            user_type = 'patient'
        elif user.is_staff:
            user_type = 'doctor'

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user_type
        })