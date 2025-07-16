# core/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Q # لإجراء بحث أو فلترة معقدة

from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote
from .serializers import (
    PatientProfileSerializer,
    BloodGlucoseReadingSerializer,
    MedicationSerializer,
    DoctorNoteSerializer,
    DoctorPatientListSerializer,
    DoctorPatientDetailSerializer,
    UserSerializer
)
from django.contrib.auth.models import User
from .permissions import IsDoctor, IsPatientOwner, IsOwnerOrDoctor # استيراد الصلاحيات المخصصة


# ViewSet للمستخدمين (للتعامل مع تسجيل الدخول/الخروج وإنشاء المستخدمين)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        # السماح بالتسجيل (create) لأي شخص (مريض)
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        # المستخدم بيقدر يشوف أو يعدل بياناته الشخصية بس
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrDoctor]
        else: # باقي العمليات (مثل list) بس للمستخدمين الإداريين (Doctors)
            permission_classes = [IsDoctor]
        return [permission() for permission in permission_classes]

    # عند إنشاء مستخدم جديد (تسجيل حساب جديد)
    def perform_create(self, serializer):
        user = serializer.save()
        # نربط المستخدم بـ PatientProfile تلقائياً لو هو مريض
        PatientProfile.objects.create(user=user)


# ViewSet لملف تعريف المريض (PatientProfile)
class PatientProfileViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    
    def get_permissions(self):
        # الطبيب (IsDoctor) له صلاحيات كاملة على كل ملفات المرضى
        # صاحب الملف (IsPatientOwner) له صلاحية رؤية وتعديل ملفه فقط
        if self.action in ['list', 'retrieve', 'create']: # عرض، جلب، إنشاء
            permission_classes = [IsDoctor | IsPatientOwner]
        elif self.action in ['update', 'partial_update', 'destroy']: # تعديل، حذف
            permission_classes = [IsPatientOwner] # المريض فقط يعدل ملفه
        else: # للـ @action decorators مثل list_for_doctor, doctor_detail, add_doctor_note
            permission_classes = [IsDoctor] # هذه الإجراءات خاصة بالأطباء
        return [permission() for permission in permission_classes]


    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff: # لو المستخدم هو طبيب
                return PatientProfile.objects.all() # الطبيب بيقدر يشوف كل ملفات المرضى
            elif hasattr(user, 'patientprofile'): # لو المستخدم مريض
                # بنرجع بس ملف تعريفه هو
                return PatientProfile.objects.filter(user=user)
        return PatientProfile.objects.none() # لو مش مسجل دخول، ما بيشوف شي


    # API خاص للطبيب: جلب قائمة المرضى اللي بيتابعهم
    # مساره: GET /api/patients/list_for_doctor/
    @action(detail=False, methods=['get']) # الصلاحية تم تحديدها في get_permissions
    def list_for_doctor(self, request):
        patients = self.get_queryset()
        serializer = DoctorPatientListSerializer(patients, many=True)
        return Response(serializer.data)

    # API خاص للطبيب: جلب تفاصيل مريض محدد
    # مساره: GET /api/patients/{id}/doctor_detail/
    @action(detail=True, methods=['get']) # الصلاحية تم تحديدها في get_permissions
    def doctor_detail(self, request, pk=None):
        patient = get_object_or_404(PatientProfile, pk=pk)
        serializer = DoctorPatientDetailSerializer(patient)
        return Response(serializer.data)

    # API خاص للطبيب: إضافة ملاحظة جديدة لمريض
    # مساره: POST /api/patients/{id}/add_doctor_note/
    @action(detail=True, methods=['post']) # الصلاحية تم تحديدها في get_permissions
    def add_doctor_note(self, request, pk=None):
        patient = get_object_or_404(PatientProfile, pk=pk)
        note_text = request.data.get('note_text')

        if not note_text:
            return Response({'error': 'Note text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        DoctorNote.objects.create(
            patient=patient,
            doctor=request.user, # الطبيب اللي عامل تسجيل دخول
            note_text=note_text
        )
        # ممكن نرجع تفاصيل المريض بعد إضافة الملاحظة عشان الواجهة تتحدث
        serializer = DoctorPatientDetailSerializer(patient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ViewSet لقراءات السكر
class BloodGlucoseReadingViewSet(viewsets.ModelViewSet):
    queryset = BloodGlucoseReading.objects.all()
    serializer_class = BloodGlucoseReadingSerializer
    permission_classes = [IsOwnerOrDoctor] # يا إما صاحب القراءة، يا إما طبيب

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff: # لو المستخدم طبيب
                # الطبيب بيشوف كل القراءات حالياً، ممكن تعديلها لاحقاً لمرضاه فقط
                return BloodGlucoseReading.objects.all()
            elif hasattr(user, 'patientprofile'): # لو المستخدم مريض
                return BloodGlucoseReading.objects.filter(patient=user.patientprofile)
        return BloodGlucoseReading.objects.none()

    def perform_create(self, serializer):
        # لما المريض بيضيف قراءة، بنربطها فيه تلقائياً
        if hasattr(self.request.user, 'patientprofile'):
            serializer.save(patient=self.request.user.patientprofile)
        else:
            raise serializers.ValidationError("Only patients can add blood glucose readings this way.")


# ViewSet للأدوية
class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    permission_classes = [IsOwnerOrDoctor] # يا إما صاحب الدواء، يا إما طبيب

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff: # لو المستخدم طبيب
                # الطبيب بيشوف كل الأدوية حالياً، ممكن تعديلها لاحقاً لمرضاه فقط
                return Medication.objects.all()
            elif hasattr(user, 'patientprofile'): # لو المستخدم مريض
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
    # الأطباء بيقدروا يعملوا كل العمليات، المرضى بيقدروا يشوفوا ملاحظاتهم
    permission_classes = [IsDoctor | IsPatientOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff: # لو المستخدم طبيب
                # بيشوف ملاحظاته هو فقط، أو ملاحظات المرضى اللي بيتابعهم
                return DoctorNote.objects.filter(doctor=user)
            elif hasattr(user, 'patientprofile'): # لو المستخدم مريض
                # بيشوف الملاحظات اللي انكتبت عنه
                return DoctorNote.objects.filter(patient=user.patientprofile)
        return DoctorNote.objects.none()

    def perform_create(self, serializer):
        # لما الطبيب يضيف ملاحظة، بنربطها فيه تلقائياً
        if self.request.user.is_staff:
            serializer.save(doctor=self.request.user)
        else:
            raise serializers.ValidationError("Only doctors can add notes.")

    def get_permissions(self):
        # لو العملية هي تحديث أو حذف، لازم يكون طبيب
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsDoctor]
        else: # باقي العمليات (عرض، إضافة)
            self.permission_classes = [IsDoctor | IsPatientOwner]
        return super().get_permissions()