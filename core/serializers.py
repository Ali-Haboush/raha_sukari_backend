# core/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import (
    PatientProfile, BloodGlucoseReading, Medication, DoctorNote,
    Attachment, Consultation, Alert, DoctorProfile, FavoriteDoctor,
    Appointment, Notification
)
from django.contrib.auth import authenticate

# --- (كل السيريالايزرز الأخرى تبقى كما هي) ---
class AuthTokenSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(
        write_only=True
    )
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    token = serializers.CharField(read_only=True)
    def validate(self, attrs):
        username_or_email = attrs.get('username_or_email')
        password = attrs.get('password')
        if not username_or_email or not password:
            raise serializers.ValidationError('يجب إدخال اسم المستخدم/الإيميل وكلمة المرور.')
        user = User.objects.filter(username__iexact=username_or_email).first()
        if user is None:
            user = User.objects.filter(email__iexact=username_or_email).first()
        if user and user.check_password(password):
            attrs['user'] = user
            return attrs
        raise serializers.ValidationError('اسم المستخدم / البريد الإلكتروني أو كلمة المرور غير صحيحة.', code='authorization')

class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[('patient', 'Patient'), ('doctor', 'Doctor')], write_only=True, required=True)
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'username': {'required': True},
            'email': {'required': True},
        }
    def create(self, validated_data):
        role = validated_data.pop('role')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        if role == 'doctor':
            user.is_staff = True
            user.save()
        return user

class PatientProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    full_name_write = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(source='user.email')
    class Meta:
        model = PatientProfile
        fields = [
            'full_name', 'address', 'gender', 'date_of_birth', 
            'phone_number', 'email', 'full_name_write'
        ]
    def update(self, instance, validated_data):
        user = instance.user
        full_name = validated_data.get('full_name_write')
        if full_name:
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        user_data = validated_data.get('user', {})
        if 'email' in user_data:
            user.email = user_data.get('email', user.email)
        user.save()
        instance.address = validated_data.get('address', instance.address)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.save()
        return instance

class PatientMedicalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ['diabetes_type', 'diagnosis_date', 'medical_notes']

class BloodGlucoseReadingSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    class Meta:
        model = BloodGlucoseReading
        fields = ['id', 'patient', 'patient_name', 'reading_value', 'reading_timestamp', 'reading_type', 'notes']
        read_only_fields = ['id', 'patient', 'reading_timestamp', 'patient_name']

class MedicationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    class Meta:
        model = Medication
        fields = ['id', 'patient', 'patient_name', 'name', 'dosage', 'frequency', 'start_date', 'end_date', 'notes']
        read_only_fields = ['id', 'patient', 'patient_name']

class DoctorNoteSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.first_name', read_only=True)
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    class Meta:
        model = DoctorNote
        fields = ['id', 'patient', 'patient_name', 'doctor', 'doctor_name', 'note_text', 'timestamp']
        read_only_fields = ['id', 'doctor', 'timestamp', 'patient_name', 'doctor_name']

class AttachmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    class Meta:
        model = Attachment
        fields = ['id', 'patient', 'patient_name', 'file', 'description', 'uploaded_at', 'file_url']
        read_only_fields = ['id', 'patient', 'patient_name', 'uploaded_at', 'file_url']
    def get_file_url(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

class ConsultationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.first_name', read_only=True)
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    patient_id = serializers.IntegerField(source='patient.id', read_only=True)
    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_id', 'patient_name', 'doctor', 'doctor_name',
            'consultation_date', 'consultation_time', 'diagnosis', 'treatment', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'patient_id', 'patient_name', 'doctor_name']
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.patient:
            representation['patient'] = PatientProfileSerializer(instance.patient, context=self.context).data
        if instance.doctor:
            representation['doctor'] = UserSerializer(instance.doctor, context=self.context).data
        return representation

class AlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    class Meta:
        model = Alert
        fields = [
            'id', 'patient', 'patient_name','name', 'alert_type', 'alert_date', 
            'alert_time', 'recurrence', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'patient', 'patient_name', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'message', 'is_read', 'timestamp']
        read_only_fields = ['id', 'recipient', 'message', 'timestamp']

# --- NEW: Serializer for Favorite Doctor LIST VIEW ---
class FavoriteDoctorListSerializer(serializers.ModelSerializer):
    # حقل مخصص لعرض اسم الطبيب الكامل
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    # حقل مخصص لحساب عدد مرات الإضافة للمفضلة
    favorites_count = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        # هنا نحدد الحقول المختصرة فقط
        fields = ['id', 'full_name', 'address', 'phone_number', 'favorites_count']
    
    def get_favorites_count(self, obj):
        # هذه الدالة تقوم بحساب عدد المرضى الذين أضافوا هذا الطبيب للمفضلة
        return obj.favorited_by_patients.count()

# --- DoctorProfile Detail Serializer (No changes needed) ---
class DoctorProfileDetailSerializer(serializers.ModelSerializer):
    # حقول مخصصة لجلب وتعديل بيانات مودل User المرتبط
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    full_name_write = serializers.CharField(write_only=True, required=False) # للكتابة فقط
    email = serializers.EmailField(source='user.email')

    class Meta:
        model = DoctorProfile
        fields = [
            'full_name',
            'address',
            'phone_number',
            'email',
            'working_hours',
            'bio'
        ]

    def update(self, instance, validated_data):
        # هذا الكود المخصص يسمح بتحديث بيانات مودل User مع بيانات DoctorProfile
        user = instance.user
        
        # تحديث الاسم الكامل (إذا تم إرساله)
        if 'full_name_write' in validated_data:
            full_name = validated_data.pop('full_name_write')
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # تحديث الإيميل (إذا تم إرساله)
        user_data = validated_data.get('user', {})
        if 'email' in user_data:
            user.email = user_data.get('email', user.email)
        
        user.save()

        # استدعاء دالة التحديث الأساسية لتحديث باقي الحقول (address, bio, etc.)
        return super().update(instance, validated_data)

# --- FavoriteDoctor Serializer (UPDATED) ---
class FavoriteDoctorSerializer(serializers.ModelSerializer):
    # تم تغيير هذا ليستخدم السيريالايزر الجديد المختصر
    doctor = FavoriteDoctorListSerializer(read_only=True)

    class Meta:
        model = FavoriteDoctor
        fields = ['id', 'doctor']


# --- (باقي الكلاسات تبقى كما هي) ---
class DoctorProfileListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'specialty', 'address', 'phone_number',
            'is_available', 'average_rating'
        ]
        read_only_fields = ['id', 'user', 'specialty', 'address', 'phone_number', 'is_available', 'average_rating']
        
class AppointmentCreateSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(write_only=True, required=False)
    patient_email = serializers.EmailField(write_only=True, required=False)
    patient_phone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Appointment
        fields = [
            'doctor', 
            'appointment_date', 
            'appointment_time', 
            'notes',
            'patient_name',
            'patient_email',
            'patient_phone'
        ]

    def create(self, validated_data):
        # هنا نقوم بحذف الحقول الوهمية قبل إرسال البيانات للمودل
        validated_data.pop('patient_name', None)
        validated_data.pop('patient_email', None)
        validated_data.pop('patient_phone', None)
        
        # الآن نقوم بإنشاء الموعد بالبيانات الصحيحة فقط
        appointment = super().create(validated_data)
        return appointment
    
# --- Appointment Serializer for VIEWING data (UPDATED) ---
class AppointmentSerializer(serializers.ModelSerializer):
    # معلومات إضافية لعرضها (للقراءة فقط)
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_number', read_only=True)
    patient_email = serializers.CharField(source='patient.user.email', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_phone', 'patient_email', 'doctor', 'doctor_name', 
            'appointment_date', 'appointment_time', 'status', 'notes'
        ]
        read_only_fields = ['patient', 'status', 'patient_name', 'doctor_name', 'patient_phone', 'patient_email']

