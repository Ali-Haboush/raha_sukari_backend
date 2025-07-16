# core/permissions.py

from rest_framework import permissions
from django.db.models import Q # لإجراء عمليات بحث وربط معقدة
from .models import PatientProfile, DoctorNote # استيراد النماذج للتحقق من نوع الكائن

# صلاحية: هل المستخدم هو مالك الكائن (البيانات) أو طبيب؟
class IsOwnerOrDoctor(permissions.BasePermission):
    """
    صلاحية مخصصة تسمح فقط لمالك الكائن أو للطبيب بالوصول.
    """
    def has_object_permission(self, request, view, obj):
        # 1. إذا كان المستخدم طبيب (is_staff)، يسمح له بالوصول دائماً
        if request.user.is_staff:
            return True

        # 2. صلاحيات القراءة (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            # إذا الكائن هو PatientProfile
            if isinstance(obj, PatientProfile):
                return obj.user == request.user
            # إذا الكائن مرتبط بـ PatientProfile (مثل BloodGlucoseReading, Medication, DoctorNote)
            if hasattr(obj, 'patient'):
                return obj.patient.user == request.user
            # إذا الكائن هو User نفسه (للوصول لبياناته الشخصية)
            if isinstance(obj, type(request.user)):
                return obj == request.user
            return False

        # 3. صلاحيات الكتابة (POST, PUT, DELETE)
        # المستخدم العادي (المريض) بيقدر يعدل بياناته الخاصة بس
        # إذا الكائن هو PatientProfile
        if isinstance(obj, PatientProfile):
            return obj.user == request.user
        # إذا الكائن BloodGlucoseReading أو Medication، المالك فقط يمكنه التعديل
        if hasattr(obj, 'patient'):
            return obj.patient.user == request.user
        # لا يسمح لأي مستخدم عادي بتعديل أو حذف DoctorNote (الطبيب فقط)
        if isinstance(obj, DoctorNote):
            return obj.doctor == request.user # الطبيب اللي كتب الملاحظة فقط بيقدر يعدلها

        return False


# صلاحية: هل المستخدم هو طبيب؟ (مبني على صلاحية IsStaff في Django)
class IsDoctor(permissions.BasePermission):
    """
    صلاحية مخصصة تسمح فقط للأطباء (المستخدمين ذوي صلاحية IsStaff) بالوصول.
    """
    def has_permission(self, request, view):
        # المستخدم يجب أن يكون مسجل دخول (Authenticated) وأن يكون IsStaff (نعتبره طبيب)
        return request.user and request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        # الطبيب لديه صلاحية الوصول لكائنات المرضى الذين يتابعهم
        # حالياً، يعتبر الطبيب لديه صلاحية رؤية كل شيء
        return self.has_permission(request, view)


# صلاحية: هل المستخدم هو المريض نفسه (Owner)؟
class IsPatientOwner(permissions.BasePermission):
    """
    صلاحية مخصصة تسمح فقط للمريض مالك البيانات بالوصول.
    """
    def has_permission(self, request, view):
        # المستخدم يجب أن يكون مسجل دخول وأن يكون لديه PatientProfile
        return request.user and request.user.is_authenticated and hasattr(request.user, 'patientprofile')

    def has_object_permission(self, request, view, obj):
        # التحقق إذا كان الكائن PatientProfile
        if isinstance(obj, PatientProfile):
            return obj.user == request.user
        # التحقق إذا كان الكائن مرتبط بـ PatientProfile (مثل BloodGlucoseReading, Medication, DoctorNote)
        if hasattr(obj, 'patient'):
            return obj.patient.user == request.user
        return False