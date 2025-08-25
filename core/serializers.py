# core/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import (
    PatientProfile, BloodGlucoseReading, Medication, DoctorNote,
    Attachment, Consultation, Alert, DoctorProfile, FavoriteDoctor,
    Appointment, Notification # <-- استيراد المودل الجديد
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
    full_name = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(choices=[('patient', 'Patient'), ('doctor', 'Doctor')], write_only=True, required=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'full_name', 'role']
        extra_kwargs = {
            'id': {'read_only': True},
            'password': {'write_only': True, 'required': True},
            'username': {'required': True},
            'first_name': {'read_only': True},
            'last_name': {'read_only': True},
        }
    def create(self, validated_data):
        role = validated_data.pop('role')
        full_name = self.initial_data.get('full_name')
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        if role == 'doctor':
            user.is_staff = True
            user.save()
        return user

class PatientProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    class Meta:
        model = PatientProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'address',
            'gender', 'date_of_birth', 'phone_number', 'diabetes_type',
            'diagnosis_date', 'medical_notes', 'profile_picture'
        ]
        read_only_fields = ['id', 'username', 'email']
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user_instance = instance.user
        for attr, value in user_data.items():
            setattr(user_instance, attr, value)
        user_instance.save()
        return super().update(instance, validated_data)

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

class DoctorProfileListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'specialty', 'address', 'phone_number',
            'is_available', 'average_rating'
        ]
        read_only_fields = ['id', 'user', 'specialty', 'address', 'phone_number', 'is_available', 'average_rating']

class DoctorProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'specialty', 'address', 'phone_number',
            'bio', 'working_hours', 'is_available', 'average_rating', 'is_favorited'
        ]
        read_only_fields = ['id', 'user', 'is_available', 'average_rating', 'is_favorited']
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(request.user, 'patientprofile'):
            return FavoriteDoctor.objects.filter(patient=request.user.patientprofile, doctor=obj).exists()
        return False

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient','patient_name', 'doctor','doctor_name', 
            'appointment_date', 'appointment_time', 'status', 'notes'
        ]
        read_only_fields = ['patient', 'status']

class FavoriteDoctorSerializer(serializers.ModelSerializer):
    doctor = DoctorProfileDetailSerializer(read_only=True)
    class Meta:
        model = FavoriteDoctor
        fields = ['id', 'doctor']

# --- NEW: Notification Serializer ---
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'message', 'is_read', 'timestamp']
        read_only_fields = ['id', 'recipient', 'message', 'timestamp']