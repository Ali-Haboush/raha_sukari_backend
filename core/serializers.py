# core/serializers.py

from rest_framework import serializers
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote, Attachment, Consultation, Alert # تم إضافة Alert
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Serializer لنموذج المستخدم الأساسي في Django
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'full_name']
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'username': {'read_only': True},
            'first_name': {'read_only': True},
            'last_name': {'read_only': True},
        }

    def create(self, validated_data):
        full_name = validated_data.pop('full_name')
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        if 'username' not in validated_data or not validated_data['username']:
            validated_data['username'] = validated_data['email']

        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            **validated_data
        )
        return user

    def update(self, instance, validated_data):
        if 'full_name' in validated_data:
            full_name = validated_data.pop('full_name')
            name_parts = full_name.split(' ', 1)
            instance.first_name = name_parts[0]
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''

        if 'email' in validated_data:
            instance.email = validated_data.get('email', instance.email)
            if instance.username == instance.email:
                instance.username = instance.email

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        instance.save()
        return instance

# Serializer لملف تعريف المريض
class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    address = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    medical_notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PatientProfile
        fields = '__all__'

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr not in ['user', 'profile_picture']:
                setattr(instance, attr, value)

        instance.save()
        return instance

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

# Serializer للمرفقات
class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = '__all__'
        read_only_fields = ['patient', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

# Serializer للاستشارات
class ConsultationSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), required=False)
    doctor = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Consultation
        fields = '__all__'
        read_only_fields = ['created_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.patient:
            representation['patient'] = PatientProfileSerializer(instance.patient, context=self.context).data
        if instance.doctor:
            representation['doctor'] = UserSerializer(instance.doctor, context=self.context).data
        return representation

# --- NEW: Alert Serializer ---
class AlertSerializer(serializers.ModelSerializer):
    # عرض تفاصيل المريض والراسل بدلاً من الـ ID فقط
    patient = serializers.PrimaryKeyRelatedField(queryset=PatientProfile.objects.all(), required=False) # يُضبط تلقائياً من الـ ViewSet
    sender_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True) # يُضبط تلقائياً من الـ ViewSet

    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ['timestamp'] # تاريخ الإنشاء يُضاف تلقائياً

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.patient:
            representation['patient'] = PatientProfileSerializer(instance.patient, context=self.context).data
        if instance.sender_user:
            representation['sender_user'] = UserSerializer(instance.sender_user, context=self.context).data
        if instance.related_reading:
            representation['related_reading'] = BloodGlucoseReadingSerializer(instance.related_reading, context=self.context).data
        return representation

# --- نهاية Alert Serializer ---

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
    attachments = AttachmentSerializer(many=True, read_only=True)
    consultations = ConsultationSerializer(many=True, read_only=True)
    alerts = AlertSerializer(many=True, read_only=True) # تم إضافة هذا السطر

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