# core/permissions.py

from rest_framework import permissions
from django.db.models import Q
# لازم نستورد PatientProfile و DoctorNote لأننا نستخدمهم في التحقق من isinstance
from .models import PatientProfile, DoctorNote
# لازم نستورد User لأننا نتحقق من صلاحية is_staff ونقارن المستخدمين
from django.contrib.auth.models import User # تم التأكد من وجود هذا الاستيراد

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
            # التحقق إذا كان الكائن PatientProfile
            if isinstance(obj, PatientProfile):
                return obj.user == request.user
            # التحقق إذا كان الكائن مرتبط بـ PatientProfile (مثل BloodGlucoseReading, Medication, DoctorNote, Attachment, Consultation)
            if hasattr(obj, 'patient'):
                return obj.patient.user == request.user
            # إذا كان الكائن هو User نفسه (للوصول لبياناته الشخصية)
            if isinstance(obj, User): # تأكد من أن obj هو نموذج User
                return obj == request.user
            return False

        # 3. صلاحيات الكتابة (POST, PUT, DELETE)
        # المستخدم العادي (المريض) بيقدر يعدل بياناته الخاصة بس
        if isinstance(obj, PatientProfile):
            return obj.user == request.user

        # إذا كان الكائن BloodGlucoseReading, Medication, Attachment, Consultation، المالك فقط يمكنه التعديل/الحذف
        if hasattr(obj, 'patient'):
            # تأكد أن المالك هو من يقوم بالتعديل/الحذف وليس طبيب (لأن الطبيب له APIs خاصة)
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
        return request.user and request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) # الطبيب له صلاحية على كل الكائنات في نطاق عمله

# صلاحية: هل المستخدم هو المريض نفسه (Owner)؟
class IsPatientOwner(permissions.BasePermission):
    """
    صلاحية مخصصة تسمح فقط للمريض مالك البيانات بالوصول.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'patientprofile')

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PatientProfile):
            return obj.user == request.user
        if hasattr(obj, 'patient'):
            return obj.patient.user == request.user
        return False

# صلاحية: هل المستخدم هو مالك البيانات (المريض) أو طبيب؟
# هذا يجمع IsPatientOwner OR IsDoctor for convenience.
class IsPatientOwnerOrDoctor(permissions.BasePermission):
    """
    صلاحية مخصصة تسمح فقط لمالك البيانات (المريض) أو للطبيب بالوصول.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if user.is_staff: # لو المستخدم طبيب
            return True

        if hasattr(user, 'patientprofile'): # لو المستخدم مريض
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False

        if user.is_staff:
            return True # الأطباء لديهم وصول كامل في سياق الكائنات

        # إذا كان المستخدم مريضاً، يسمح له بالوصول إلى كائناته الخاصة فقط
        if hasattr(user, 'patientprofile'):
            if isinstance(obj, PatientProfile):
                return obj.user == user
            if hasattr(obj, 'patient'): # ينطبق على BloodGlucoseReading, Medication, Attachment, Consultation, DoctorNote
                return obj.patient.user == user
            if isinstance(obj, User):
                return obj == user
        return False
    # --- هذا هو الكود الجديد الذي سنضيفه ---
class IsProfileOwner(permissions.BasePermission):
    """
    صلاحية مخصصة للتأكد من أن المستخدم الحالي هو صاحب الملف الشخصي.
    """
    def has_object_permission(self, request, view, obj):
        # obj هنا هو DoctorProfile أو PatientProfile
        # نتحقق إذا كان المستخدم المرتبط بالملف الشخصي هو نفس المستخدم الذي أرسل الطلب
        return obj.user == request.user
    
class IsPatient(permissions.BasePermission):
    """
    صلاحية مخصصة للتحقق من أن المستخدم هو مريض.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'patientprofile')
    
# --- NEW Permissions for Consultations ---
class IsDoctorOrReadOnly(permissions.BasePermission):
    """
    يسمح للطبيب فقط بإنشاء وتعديل الاستشارات، بينما يسمح للآخرين (المريض) بالعرض فقط.
    """
    def has_permission(self, request, view):
        # أي مستخدم مسجل دخوله يمكنه العرض (GET)
        if request.method in permissions.SAFE_METHODS:
            return True
        # فقط الأطباء يمكنهم الإنشاء والتعديل (POST, PUT, PATCH)
        return request.user.is_authenticated and request.user.is_staff

class IsPatientOwnerOfConsultation(permissions.BasePermission):
    """
    يسمح فقط للمريض صاحب الاستشارة بحذفها.
    """
    def has_object_permission(self, request, view, obj):
        return obj.patient.user == request.user