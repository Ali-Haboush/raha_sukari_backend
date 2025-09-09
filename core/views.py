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
from rest_framework import mixins
from drf_spectacular.utils import extend_schema


from .models import (
    PatientProfile, BloodGlucoseReading, Medication, DoctorNote, Attachment,
    Consultation, Alert, User, DoctorProfile, FavoriteDoctor, Appointment,
    Notification 
)
from .serializers import (
    UserSerializer, PatientProfileSerializer, BloodGlucoseReadingSerializer,
    MedicationSerializer, DoctorNoteSerializer, AttachmentSerializer,
    AuthTokenSerializer, 
    ConsultationSerializer, AlertSerializer,
    FavoriteDoctorSerializer, AppointmentSerializer,
    NotificationSerializer, PatientMedicalDataSerializer,
    AppointmentCreateSerializer, PatientListForDoctorSerializer,
    DoctorProfileSerializer,
    DoctorProfileListSerializer, 
    FavoriteDoctorListSerializer, PatientAppointmentSerializer, DoctorAppointmentListSerializer, DoctorAppointmentUpdateSerializer,
    AppointmentRespondSerializer  
)

from .permissions import IsDoctor, IsPatientOwner, IsOwnerOrDoctor, IsPatientOwnerOrDoctor, IsProfileOwner, IsPatient, IsDoctorOrReadOnly, IsPatientOwnerOfConsultation


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

class PatientProfileViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    
    def get_permissions(self):
        """
        هذه الدالة تضع القواعد الأمنية:
        - للتعديل (update/patch): يجب أن تكون مالك الحساب (مريض فقط).
        - لباقي العمليات (العرض): يمكن للمالك أو الطبيب.
        """
        if self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, IsPatientOwner]
        else:
            self.permission_classes = [IsAuthenticated, IsPatientOwnerOrDoctor]
        return super().get_permissions()

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
        
    @action(detail=True, methods=['get', 'patch'], url_path='medical-data', serializer_class=PatientMedicalDataSerializer)
    def medical_data(self, request, pk=None):
        # ... (هذه الدالة تبقى كما هي)
        patient_profile = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(patient_profile)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = self.get_serializer(patient_profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

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

 # --- ConsultationViewSet (UPDATED with new permissions) ---
class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    
    def get_permissions(self):
        """
        هنا بنحدد الصلاحيات بناءً على نوع الطلب:
        - الحذف (destroy): فقط للمريض صاحب الاستشارة.
        - باقي الطلبات: الطبيب له صلاحيات كاملة، والمريض له صلاحية العرض فقط.
        """
        if self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, IsPatientOwnerOfConsultation]
        else:
            self.permission_classes = [IsAuthenticated, IsDoctorOrReadOnly]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # إذا كان المستخدم مريض، نعرض له استشاراته فقط
            if hasattr(user, 'patientprofile'):
                return Consultation.objects.filter(patient=user.patientprofile)
            # إذا كان طبيب، نعرض له كل الاستشارات (يمكن تحسينها لاحقاً)
            elif user.is_staff:
                return Consultation.objects.all()
        return Consultation.objects.none()

    def perform_create(self, serializer):
        # هذا المنطق يضمن أن الطبيب هو من ينشئ الاستشارة ويربطها بنفسه
        serializer.save(doctor=self.request.user)

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

# --- DoctorProfile ViewSet (UPDATED with 'personal_data' action) ---
class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    # هذا الـ ViewSet الآن وظيفته الأساسية هي عرض قائمة الأطباء وتفاصيلهم فقط
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileListSerializer # Sserializer الافتراضي لعرض القائمة

    @action(detail=False, methods=['get'], url_path='my-patients', serializer_class=PatientListForDoctorSerializer)
    def list_patients(self, request):
        # هنا نتأكد أن المستخدم هو طبيب
        if not hasattr(request.user, 'doctorprofile'):
            return Response({'error': 'User is not a doctor.'}, status=status.HTTP_403_FORBIDDEN)
        
        doctor_profile = request.user.doctorprofile
        # هنا نجلب قائمة المرضى المرتبطين بهذا الطبيب
        patients = doctor_profile.patients.all()
        
        serializer = self.get_serializer(patients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='remove-patient-from-list')
    def remove_patient(self, request, pk=None):
        # هنا نتأكد أن المستخدم هو طبيب
        if not hasattr(request.user, 'doctorprofile'):
            return Response({'error': 'User is not a doctor.'}, status=status.HTTP_403_FORBIDDEN)

        doctor_profile = request.user.doctorprofile
        try:
            # pk هنا هو ID المريض الذي نريد حذفه
            patient_to_remove = doctor_profile.patients.get(pk=pk)
            # هنا نزيله من قائمة الطبيب
            doctor_profile.patients.remove(patient_to_remove)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PatientProfile.DoesNotExist:
            return Response({'error': 'Patient not found in your list.'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get', 'patch'], url_path='profile', serializer_class=DoctorProfileSerializer, permission_classes=[IsAuthenticated, IsDoctor])
    def profile(self, request):
        # الكود يجد الطبيب تلقائياً من التوكن
        doctor_profile = request.user.doctorprofile
        
        if request.method == 'GET':
            serializer = self.get_serializer(doctor_profile)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = self.get_serializer(doctor_profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
    @action(detail=True, methods=['post'], url_path='add-me', permission_classes=[IsAuthenticated, IsPatient])
    def add_patient_to_doctor_list(self, request, pk=None):
        # هنا بنجيب بروفايل الدكتور المطلوب من الرابط
        doctor_profile = self.get_object()
        # هنا بنجيب بروفايل المريض اللي مسجل دخول من التوكن
        patient_profile = request.user.patientprofile

        # هنا بنضيف المريض لقائمة الطبيب
        doctor_profile.patients.add(patient_profile)
        
        return Response({'status': 'Patient added to doctor list'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsPatient])
    def favorite(self, request, pk=None):
        # ... (الكود كما هو)
        doctor = self.get_object()
        patient_profile = request.user.patientprofile
        favorite, created = FavoriteDoctor.objects.get_or_create(patient=patient_profile, doctor=doctor)
        if created:
            return Response({'status': 'تم إضافة الطبيب إلى المفضلة'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'status': 'هذا الطبيب موجود بالفعل في المفضلة'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unfavorite', permission_classes=[IsPatient])
    def unfavorite(self, request, pk=None):
        # ... (الكود كما هو)
        doctor = self.get_object()
        patient_profile = request.user.patientprofile
        deleted_count, _ = FavoriteDoctor.objects.filter(patient=patient_profile, doctor=doctor).delete()
        if deleted_count > 0:
            return Response({'status': 'تم حذف الطبيب من المفضلة'}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'الطبيب ليس في المفضلة أصلاً'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='favorites', permission_classes=[IsPatient])
    def list_favorites(self, request):
        patient_profile = request.user.patientprofile
        favorites = FavoriteDoctor.objects.filter(patient=patient_profile)
        if not favorites.exists():
            return Response({"message": "لا يوجد لديك أطباء مفضلين بعد."})
        serializer = FavoriteDoctorSerializer(favorites, many=True, context={'request': request})
        return Response(serializer.data)



# --- AppointmentViewSet  ---
class AppointmentViewSet(viewsets.ModelViewSet):
    pagination_class = None
    queryset = Appointment.objects.all().order_by('appointment_date', 'appointment_time')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'appointment_date'] 
    ordering_fields = ['appointment_date', 'appointment_time']

    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentCreateSerializer
        if self.action in ['update', 'partial_update']:
            return DoctorAppointmentUpdateSerializer
        if self.action == 'respond': # أضفنا هذا الشرط لـ respond
            return AppointmentRespondSerializer
        if hasattr(self.request.user, 'doctorprofile'):
            return DoctorAppointmentListSerializer
        if hasattr(self.request.user, 'patientprofile'):
            return PatientAppointmentSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'patientprofile'):
            # المريض يرى كل مواعيده بكل الحالات (مقبول، مرفوض، قيد الانتظار)
            return self.queryset.filter(patient=user.patientprofile)
        elif hasattr(user, 'doctorprofile'):
            return self.queryset.filter(doctor=user.doctorprofile).exclude(status='Rejected')
        return Appointment.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            appointment = serializer.save(patient=self.request.user.patientprofile)
            doctor_user = appointment.doctor.user
            patient_name = appointment.patient.user.get_full_name()
            message = f"لديك طلب موعد جديد من المريض: {patient_name}"
            Notification.objects.create(recipient=doctor_user, message=message, related_object=appointment)
        else:
            raise serializers.ValidationError("Only patients can create appointments.")

    def perform_update(self, serializer):
        if self.request.user.is_staff and serializer.instance.doctor.user == self.request.user:
            serializer.save()
        else:
            raise serializers.ValidationError("You do not have permission to edit this appointment.")

    
    @extend_schema(
        request=AppointmentRespondSerializer,
        responses={
            200: {'description': 'تم الرد على الموعد بنجاح.'},
            400: {'description': 'طلب غير صالح (مثلاً: تم الرد على الموعد مسبقاً).'},
        }
    )
    @action(
        detail=True, 
        methods=['post'], 
        url_path='respond', 
        permission_classes=[IsAuthenticated, IsDoctor]
    )
    def respond(self, request, pk=None):
        appointment = self.get_object()
        
        if appointment.status != 'Pending':
            return Response(
                {'error': 'This appointment has already been responded to.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accepted = serializer.validated_data['accepted']

        if accepted:
            appointment.status = 'Confirmed'
            doctor_profile = request.user.doctorprofile
            patient_profile = appointment.patient
            doctor_profile.patients.add(patient_profile)
            message = "تم قبول الموعد بنجاح."
        else:
            appointment.status = 'Rejected'
            message = "تم رفض الموعد."
            
        appointment.save()
        
        notification_message = f"لقد تم {appointment.get_status_display()} موعدك مع د. {appointment.doctor.user.get_full_name()}"
        Notification.objects.create(
            recipient=appointment.patient.user, 
            message=notification_message,
            related_object=appointment
        )
        
        return Response({'status': message, 'appointment_status': appointment.status}, status=status.HTTP_200_OK)



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