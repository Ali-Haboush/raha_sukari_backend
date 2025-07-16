# core/serializers.py

from rest_framework import serializers
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote
from django.contrib.auth.models import User

# Serializer لنموذج المستخدم الأساسي في Django
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'required': True} # لضمان إدخال كلمة مرور وعدم إظهارها في الرد، ولجعلها مطلوبة
        }

    def create(self, validated_data):
        # دالة خاصة لإنشاء مستخدم جديد مع تشفير كلمة المرور
        user = User.objects.create_user(**validated_data)
        return user

# Serializer لملف تعريف المريض
class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) # لربط ملف تعريف المريض بالمستخدم (للقراءة فقط)

    class Meta:
        model = PatientProfile
        fields = '__all__'

# Serializer لقراءة السكر
class BloodGlucoseReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodGlucoseReading
        fields = '__all__'

# Serializer للدواء
class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

# Serializer لملاحظات الطبيب
class DoctorNoteSerializer(serializers.ModelSerializer):
    doctor = UserSerializer(read_only=True) # لإظهار معلومات الطبيب الذي كتب الملاحظة

    class Meta:
        model = DoctorNote
        fields = '__all__'

# --- Serializers خاصة بواجهات الطبيب ---

# Serializer مخصص لعرض قائمة المرضى للطبيب
class DoctorPatientListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) # لإظهار معلومات المستخدم (المريض) الأساسية في القائمة

    class Meta:
        model = PatientProfile
        fields = ['id', 'user', 'diabetes_type', 'diagnosis_date']

# Serializer مخصص لعرض تفاصيل مريض محدد للطبيب
class DoctorPatientDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    glucose_readings = BloodGlucoseReadingSerializer(many=True, read_only=True) # لعرض كل قراءات السكر للمريض
    medications = MedicationSerializer(many=True, read_only=True) # لعرض كل الأدوية للمريض
    doctor_notes = DoctorNoteSerializer(many=True, read_only=True) # لعرض كل ملاحظات الطبيب عن المريض

    class Meta:
        model = PatientProfile
        fields = '__all__'