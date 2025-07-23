# core/serializers.py

from rest_framework import serializers
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote
from django.contrib.auth.models import User
from django.contrib.auth import authenticate # لاستخدام دالة authenticate المدمجة

# Serializer لنموذج المستخدم الأساسي في Django
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'required': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# Serializer لملف تعريف المريض
class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

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
    doctor = UserSerializer(read_only=True)

    class Meta:
        model = DoctorNote
        fields = ['id', 'patient', 'doctor', 'note_text', 'timestamp']

# --- Serializers خاصة بواجهات الطبيب ---

class DoctorPatientListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = PatientProfile
        fields = ['id', 'user', 'diabetes_type', 'diagnosis_date']

class DoctorPatientDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    glucose_readings = BloodGlucoseReadingSerializer(many=True, read_only=True)
    medications = MedicationSerializer(many=True, read_only=True)
    doctor_notes = DoctorNoteSerializer(many=True, read_only=True)

    class Meta:
        model = PatientProfile
        fields = '__all__'

# --- Serializer جديد لتسجيل الدخول بالبريد الإلكتروني أو اسم المستخدم ---
class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True, required=False) # ممكن يكون اسم مستخدم
    email = serializers.EmailField(write_only=True, required=False) # أو بريد إلكتروني
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')

        if not (username or email):
            raise serializers.ValidationError(
                'يجب تزويد اسم المستخدم أو البريد الإلكتروني.',
                code='authorization'
            )
        if not password:
             raise serializers.ValidationError(
                'يجب تزويد كلمة السر.',
                code='authorization'
            )

        # محاولة المصادقة باستخدام البريد الإلكتروني أو اسم المستخدم
        user = None
        if email:
            try:
                # نبحث عن المستخدم بالبريد الإلكتروني
                user = User.objects.get(email=email)
                user = authenticate(request=self.context.get('request'), username=user.username, password=password)
            except User.DoesNotExist:
                pass # اذا الايميل مش موجود، بنكمل للمرحلة اللي بعدها (ممكن يكون اسم مستخدم)

        if user is None and username:
            # اذا ما لقينا بالايميل، بنجرب اسم المستخدم
            user = authenticate(request=self.context.get('request'), username=username, password=password)

        if not user:
            # اذا لا بالايميل ولا باسم المستخدم، يعني فشل
            raise serializers.ValidationError(
                'غير قادر على تسجيل الدخول ببيانات الدخول المزودة.',
                code='authorization'
            )

        attrs['user'] = user
        return attrs