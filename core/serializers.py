# core/serializers.py

from rest_framework import serializers
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Serializer لنموذج المستخدم الأساسي في Django (تم تعديل حقول الإدخال والإخراج)
class UserSerializer(serializers.ModelSerializer):
    # هذا الحقل سيتم استقباله من الواجهة الأمامية كاسم كامل
    full_name = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        # هذه الحقول هي التي سيتم استقبالها من الواجهة الأمامية وإخراجها في الرد
        # full_name هو فقط للإدخال (write_only)
        # password هو فقط للإدخال (write_only)
        # username, first_name, last_name, email, id هي للإخراج أيضاً
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'full_name']
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            # نحدد أن هذه الحقول للقراءة فقط عند الإخراج، لأننا نتحكم في قيمها عند الإنشاء
            'username': {'read_only': True},
            'first_name': {'read_only': True},
            'last_name': {'read_only': True},
        }

    def create(self, validated_data):
        # نقوم بإزالة 'full_name' من البيانات لأنها ليست حقلاً مباشراً في نموذج User
        full_name = validated_data.pop('full_name')

        # نقوم بتقسيم الاسم الكامل إلى اسم أول واسم أخير
        name_parts = full_name.split(' ', 1) # نقسم عند أول مسافة فقط
        first_name = name_parts[0]
        # إذا كان هناك جزء ثانٍ بعد المسافة الأولى، فهو اسم العائلة، وإلا فاسم العائلة فارغ
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # إذا لم يتم توفير اسم مستخدم (وهذا هو الحال في الواجهة الجديدة التي تعتمد على البريد الإلكتروني)
        # نستخدم البريد الإلكتروني كاسم مستخدم تلقائياً
        if 'username' not in validated_data or not validated_data['username']:
            validated_data['username'] = validated_data['email']

        # نقوم بإنشاء المستخدم باستخدام البيانات المعالجة
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            **validated_data # هذه تحتوي على username, email, password
        )
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

# --- Serializer لتسجيل الدخول بالبريد الإلكتروني أو اسم المستخدم ---
class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
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

        user = None
        if email:
            try:
                user = User.objects.get(email=email)
                user = authenticate(request=self.context.get('request'), username=user.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None and username:
            user = authenticate(request=self.context.get('request'), username=username, password=password)

        if not user:
            raise serializers.ValidationError(
                'غير قادر على تسجيل الدخول ببيانات الدخول المزودة.',
                code='authorization'
            )

        attrs['user'] = user
        return attrs