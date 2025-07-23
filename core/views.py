# core/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote
from .serializers import (
    PatientProfileSerializer,
    BloodGlucoseReadingSerializer,
    MedicationSerializer,
    DoctorNoteSerializer,
    DoctorPatientListSerializer,
    DoctorPatientDetailSerializer,
    UserSerializer,
    AuthTokenSerializer # استيراد السيريالايزر الجديد
)
from django.contrib.auth.models import User
from .permissions import IsDoctor, IsPatientOwner, IsOwnerOrDoctor

from rest_framework.authtoken.models import Token # لاستخدام نموذج التوكن
from rest_framework.authtoken.views import ObtainAuthToken as OriginalObtainAuthToken # استيراد الأصلية


# ViewSet للمستخدمين (للتعامل مع تسجيل الدخول/الخروج وإنشاء المستخدمين)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrDoctor]
        else:
            permission_classes = [IsDoctor]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        user = serializer.save()
        PatientProfile.objects.create(user=user)


# ViewSet لملف تعريف المريض (PatientProfile)
class PatientProfileViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            permission_classes = [IsDoctor | IsPatientOwner]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsPatientOwner]
        else:
            permission_classes = [IsDoctor]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return PatientProfile.objects.all()
            elif hasattr(user, 'patientprofile'):
                return PatientProfile.objects.filter(user=user)
        return PatientProfile.objects.none()

    @action(detail=False, methods=['get'])
    def list_for_doctor(self, request):
        patients = self.get_queryset()
        serializer = DoctorPatientListSerializer(patients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def doctor_detail(self, request, pk=None):
        patient = get_object_or_404(PatientProfile, pk=pk)
        serializer = DoctorPatientDetailSerializer(patient)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_doctor_note(self, request, pk=None):
        patient = get_object_or_404(PatientProfile, pk=pk)
        note_text = request.data.get('note_text')

        if not note_text:
            return Response({'error': 'Note text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        DoctorNote.objects.create(
            patient=patient,
            doctor=request.user,
            note_text=note_text
        )
        serializer = DoctorPatientDetailSerializer(patient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ViewSet لقراءات السكر
class BloodGlucoseReadingViewSet(viewsets.ModelViewSet):
    queryset = BloodGlucoseReading.objects.all()
    serializer_class = BloodGlucoseReadingSerializer
    permission_classes = [IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return BloodGlucoseReading.objects.all()
            elif hasattr(user, 'patientprofile'):
                return BloodGlucoseReading.objects.filter(patient=user.patientprofile)
        return BloodGlucoseReading.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can add blood glucose readings this way.")


# ViewSet للأدوية
class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    permission_classes = [IsOwnerOrDoctor]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return Medication.objects.all()
            elif hasattr(user, 'patientprofile'):
                return Medication.objects.filter(patient=user.patientprofile)
        return Medication.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can add medications this way.")


# ViewSet لملاحظات الطبيب (إضافة وعرض)
class DoctorNoteViewSet(viewsets.ModelViewSet):
    queryset = DoctorNote.objects.all()
    serializer_class = DoctorNoteSerializer
    permission_classes = [IsDoctor | IsPatientOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return DoctorNote.objects.filter(doctor=user)
            elif hasattr(user, 'patientprofile'):
                return DoctorNote.objects.filter(patient=user.patientprofile)
        return DoctorNote.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_staff:
            serializer.save(doctor=self.request.user)
        else:
            raise serializers.ValidationError("Only doctors can add notes.")

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsDoctor]
        else:
            self.permission_classes = [IsDoctor | IsPatientOwner]
        return super().get_permissions()

# --- Viewset جديد لتسجيل الدخول بالبريد الإلكتروني أو اسم المستخدم ---
class ObtainAuthToken(OriginalObtainAuthToken):
    serializer_class = AuthTokenSerializer # استخدام السيريالايزر المخصص بتاعنا

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        })