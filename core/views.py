# core/views.py

from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML, CSS
from django.utils import timezone
import os

from rest_framework.decorators import api_view, authentication_classes, permission_classes, action
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework import serializers


from .models import (
    PatientProfile, BloodGlucoseReading, Medication, DoctorNote, Attachment,
    Consultation, Alert, User, DoctorProfile, FavoriteDoctor, Appointment,
    Notification 
)
from .serializers import (
    UserSerializer, PatientProfileSerializer, BloodGlucoseReadingSerializer,
    MedicationSerializer, DoctorNoteSerializer, AttachmentSerializer,
    AuthTokenSerializer, DoctorProfileListSerializer, DoctorProfileDetailSerializer,
    ConsultationSerializer, AlertSerializer,
    FavoriteDoctorSerializer, AppointmentSerializer,
    NotificationSerializer 
)
from .permissions import IsDoctor, IsPatientOwner, IsOwnerOrDoctor, IsPatientOwnerOrDoctor

# --- (كل الكلاسات السابقة تبقى كما هي بدون تغيير) ---
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

class CustomAuthToken(ObtainAuthToken):
    serializer_class = AuthTokenSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        user_type = None
        patient_profile_id = None
        if hasattr(user, 'patientprofile'):
            user_type = 'patient'
            patient_profile_id = user.patientprofile.id
        elif user.is_staff:
            user_type = 'doctor'
        return Response({
            'token': token.key, 'user_id': user.pk, 'patient_profile_id': patient_profile_id,
            'username': user.username, 'email': user.email, 'first_name': user.first_name,
            'last_name': user.last_name, 'user_type': user_type
        })

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

class BloodGlucoseReadingViewSet(viewsets.ModelViewSet):
    queryset = BloodGlucoseReading.objects.all()
    serializer_class = BloodGlucoseReadingSerializer
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
    context = {'consultation': consultation, 'patient': consultation.patient, 'doctor': consultation.doctor, 'now': timezone.now()}
    html_string = render_to_string('core/consultation_report.html', context)
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="consultation_report_{consultation.id}.pdf"'
    return response

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

class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, IsPatientOwner]
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'patientprofile'):
            return Alert.objects.filter(patient=user.patientprofile).order_by('alert_date', 'alert_time')
        return Alert.objects.none()
    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can create alerts.")
    @action(detail=False, methods=['post'], url_path='toggle-all')
    def toggle_all(self, request):
        new_status = request.data.get('is_active')
        if new_status not in [True, False]:
            return Response({'error': "You must provide an 'is_active' field with a boolean value (true or false)."}, status=status.HTTP_400_BAD_REQUEST)
        patient_profile = request.user.patientprofile
        updated_count = Alert.objects.filter(patient=patient_profile).update(is_active=new_status)
        status_word = "activated" if new_status else "deactivated"
        return Response({'status': f'All {updated_count} alerts have been {status_word}.'}, status=status.HTTP_200_OK)

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileDetailSerializer
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorProfileListSerializer
        elif self.action in ['favorite', 'unfavorite']:
            return FavoriteDoctorSerializer
        return DoctorProfileDetailSerializer
    def get_queryset(self):
        if hasattr(self.request.user, 'patientprofile'):
            return DoctorProfile.objects.filter(user__is_staff=True, is_available=True).order_by('user__first_name')
        elif self.request.user.is_staff:
            return DoctorProfile.objects.filter(user__is_staff=True).order_by('user__first_name')
        return DoctorProfile.objects.none()
    @action(detail=True, methods=['post'], permission_classes=[IsPatientOwner])
    def favorite(self, request, pk=None):
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        patient_profile = request.user.patientprofile
        favorite, created = FavoriteDoctor.objects.get_or_create(patient=patient_profile, doctor=doctor)
        if created:
            return Response({'status': 'تم إضافة الطبيب إلى المفضلة'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'status': 'هذا الطبيب موجود بالفعل في المفضلة'}, status=status.HTTP_200_OK)
    @action(detail=True, methods=['delete'], permission_classes=[IsPatientOwner])
    def unfavorite(self, request, pk=None):
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        patient_profile = request.user.patientprofile
        favorite = get_object_or_404(FavoriteDoctor, patient=patient_profile, doctor=doctor)
        favorite.delete()
        return Response({'status': 'تم حذف الطبيب من المفضلة'}, status=status.HTTP_204_NO_CONTENT)
    @action(detail=False, methods=['get'], url_path='favorites', permission_classes=[IsPatientOwner])
    def list_favorites(self, request):
        patient_profile = request.user.patientprofile
        favorites = FavoriteDoctor.objects.filter(patient=patient_profile)
        serializer = FavoriteDoctorSerializer(favorites, many=True, context={'request': request})
        return Response(serializer.data)

# --- Appointment ViewSet (UPDATED to create Notifications) ---
class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by('appointment_date', 'appointment_time')
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['appointment_date', 'status']
    ordering_fields = ['appointment_date', 'appointment_time']
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'patientprofile'):
            return self.queryset.filter(patient=user.patientprofile)
        elif hasattr(user, 'doctorprofile'):
            return self.queryset.filter(doctor=user.doctorprofile)
        return Appointment.objects.none()
    
    def perform_create(self, serializer):
        # --- هذا هو الجزء الذي تم تعديله ---
        if hasattr(self.request.user, 'patientprofile'):
            # أولاً، نحفظ الموعد لنحصل على كل تفاصيله
            appointment = serializer.save(patient=self.request.user.patientprofile)
            
            # ثانياً، نقوم بإنشاء الإشعار
            doctor_user = appointment.doctor.user
            patient_name = appointment.patient.user.get_full_name()
            message = f"لديك طلب موعد جديد من المريض: {patient_name}"
            Notification.objects.create(recipient=doctor_user, message=message, related_object=appointment)
        else:
            raise serializers.ValidationError("Only patients can create appointments.")

    def perform_update(self, serializer):
        instance = serializer.instance
        if self.request.user.is_staff and instance.doctor.user == self.request.user:
            serializer.save()
        else:
            raise serializers.ValidationError("You do not have permission to edit this appointment.")

# --- NEW: Notification ViewSet ---
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)
