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

# --- AuthToken Serializer ---
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

# --- User Serializer ---
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
        
        
        is_staff_flag = (role == 'doctor')

        # نستخدم create() بدلاً من create_user() للتحكم الكامل
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            is_staff=is_staff_flag  #  نحدد الدور هنا
        )
        # نقوم بتشفير كلمة المرور يدوياً لأننا لم نستخدم create_user
        user.set_password(validated_data['password'])
        user.save()
        
        return user

# --- PatientProfile Serializer ---
class PatientProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name')
    email = serializers.EmailField(source='user.email')
    class Meta:
        model = PatientProfile
        fields = [
            'full_name', 'address', 'gender', 'date_of_birth', 
            'phone_number', 'email'
        ]
    def update(self, instance, validated_data):
        # هنا بنفصل بيانات اليوزر (الاسم والإيميل) عن باقي البيانات
        user_data = validated_data.pop('user', {})
        user = instance.user

        # هنا بنتعامل مع تحديث الاسم الكامل
        if 'get_full_name' in user_data:
            full_name = user_data.get('get_full_name')
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''

        # هنا بنتعامل مع تحديث الإيميل
        if 'email' in user_data:
            user.email = user_data.get('email', user.email)

        user.save()

        # السطر الأخير يقوم بتحديث باقي الحقول تلقائياً (العنوان، الهاتف، إلخ)
        return super().update(instance, validated_data)
    
    # : Serializer for Doctor's Patient List View ---
class PatientListForDoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name')
    phone_number = serializers.CharField()

    class Meta:
        model = PatientProfile
        fields = ['id', 'full_name', 'phone_number', 'diabetes_type']

# --- PatientMedicalData Serializer ---
class PatientMedicalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ['diabetes_type', 'diagnosis_date', 'medical_notes']

# --- BloodGlucoseReading Serializer ---
class BloodGlucoseReadingSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    class Meta:
        model = BloodGlucoseReading
        fields = ['id', 'patient', 'patient_name', 'reading_value', 'reading_timestamp', 'reading_type', 'notes']
        read_only_fields = ['id', 'patient', 'reading_timestamp', 'patient_name']

# --- Medication Serializer ---
class MedicationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    class Meta:
        model = Medication
        fields = ['id', 'patient', 'patient_name', 'name', 'dosage', 'frequency', 'start_date', 'end_date', 'notes']
        read_only_fields = ['id', 'patient', 'patient_name']

# --- DoctorNote Serializer ---
class DoctorNoteSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.first_name', read_only=True)
    patient_name = serializers.CharField(source='patient.user.first_name', read_only=True)
    class Meta:
        model = DoctorNote
        fields = ['id', 'patient', 'patient_name', 'doctor', 'doctor_name', 'note_text', 'timestamp']
        read_only_fields = ['id', 'doctor', 'timestamp', 'patient_name', 'doctor_name']

# --- Attachment Serializer ---
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

# --- Consultation Serializer (Cleaned for UI) ---
class ConsultationSerializer(serializers.ModelSerializer):
    # هنا بنجيب اسم الطبيب بشكل للقراءة فقط
    doctor_name = serializers.CharField(source='doctor.first_name', read_only=True)

    class Meta:
        model = Consultation
        # هذه هي الحقول فقط التي تظهر في الواجهة
        fields = [
            'id',
            'consultation_date',
            'consultation_time',
            'doctor_name',

            'diagnosis',
            'treatment',
            'notes', # حقل الملاحظات الإضافي
            'patient' # هذا الحقل مطلوب عند الإنشاء ليتم ربط المراجعة بالمريض
        ]
        extra_kwargs = {
            'patient': {'write_only': True} # نجعل حقل المريض للكتابة فقط
        }

# --- NEW: Serializer for a Doctor to Add Diagnosis and Treatment ---
class ConsultationDiagnoseSerializer(serializers.Serializer):
    """
    Serializer مخصص للتحقق من بيانات التشخيص والعلاج التي يرسلها الطبيب.
    """
    diagnosis = serializers.CharField(required=True)
    treatment = serializers.CharField(required=True)

    class Meta:
        # هذه الحقول ليست مرتبطة مباشرة بموديل، بل هي مدخلات لعملية معينة
        fields = ['diagnosis', 'treatment'] 
               
# --- Alert Serializer ---
class AlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    class Meta:
        model = Alert
        fields = [
            'id', 'patient', 'patient_name','name', 'alert_type', 'alert_date', 
            'alert_time', 'recurrence', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'patient', 'patient_name', 'created_at']

# --- Notification Serializer ---
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'message', 'is_read', 'timestamp']
        read_only_fields = ['id', 'recipient', 'message', 'timestamp']

# --- NEW: Serializer for Doctor's Personal Data ONLY ---
class DoctorProfileSerializer(serializers.ModelSerializer):
    """
    Serializer يستخدمه الطبيب لتحديث بياناته الشخصية.
    تم إصلاح دالة update هنا لحل مشكلة PATCH.
    """
    full_name = serializers.CharField(source='user.get_full_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = DoctorProfile
        fields = [
            'full_name',
            'address',
            'phone_number',
            'email',
            'working_hours',
            'bio', # المؤهلات
        ]

    def update(self, instance, validated_data):
        """
        النسخة النهائية والصحيحة لدالة التحديث التي تتعامل مع البيانات المتداخلة.
        """
        # 1. نستخرج بيانات المستخدم المتداخلة إذا كانت موجودة
        user_data = validated_data.pop('user', {})
        user = instance.user

        # 2. نقوم بتحديث بيانات موديل User
        if 'get_full_name' in user_data:
            full_name = user_data.get('get_full_name')
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if 'email' in user_data:
            user.email = user_data.get('email', user.email)
        
        user.save()

        # 3. نقوم بتحديث بيانات موديل DoctorProfile باستخدام الطريقة الافتراضية الآمنة
        # validated_data الآن تحتوي فقط على حقول DoctorProfile
        return super().update(instance, validated_data)

    
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
class DoctorCreateSerializer(serializers.ModelSerializer):
    # نستقبل بيانات إنشاء المستخدم الأساسي مع البروفايل في طلب واحد
    user = UserSerializer()

    class Meta:
        model = DoctorProfile
        # هذه هي الحقول التي نريد استقبالها عند إنشاء طبيب جديد
        fields = [
            'user',
            'specialty',
            'address',
            'phone_number',
            'bio',
            'working_hours'
        ]

    def create(self, validated_data):
        # نستخرج بيانات المستخدم ونقوم بإنشائه أولاً
        user_data = validated_data.pop('user')
        # نتأكد من أن role هو doctor
        user_data['role'] = 'doctor' 
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
     
        doctor_profile = DoctorProfile.objects.get(user=user)
        doctor_profile.specialty = validated_data.get('specialty', '')
        doctor_profile.address = validated_data.get('address', '')
        doctor_profile.phone_number = validated_data.get('phone_number', '')
        doctor_profile.bio = validated_data.get('bio', '')
        doctor_profile.working_hours = validated_data.get('working_hours', '')
        doctor_profile.save()
        
        return doctor_profile
    
class AppointmentSerializer(serializers.ModelSerializer):
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

# --- AppointmentCreateSerializer (Corrected) ---
class AppointmentCreateSerializer(serializers.ModelSerializer):
    # تعريف الحقول الإضافية كحقول للكتابة فقط
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
        # هنا نقوم بحذف الحقول الإضافية قبل الحفظ في قاعدة البيانات
        validated_data.pop('patient_name', None)
        validated_data.pop('patient_email', None)
        validated_data.pop('patient_phone', None)
        
        appointment = Appointment.objects.create(**validated_data)
        return appointment
    
class DoctorAppointmentListSerializer(serializers.ModelSerializer):
    # هنا بنجيب اسم المريض بس
     patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)

     class Meta:
        model = Appointment
        # هنا بنعرض بس اسم المريض وتاريخ ووقت الحجز
        fields = ['id', 'patient_name', 'appointment_date', 'appointment_time']

DAYS_AR = {
    'Saturday': 'السبت', 'Sunday': 'الأحد', 'Monday': 'الإثنين',
    'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس',
    'Friday': 'الجمعة'
}

# --- NEW: Serializer for Patient's Appointment View ---
class PatientAppointmentSerializer(serializers.ModelSerializer):
    # هنا بنجيب اسم الطبيب وتخصصه
    doctor_name = serializers.CharField(source='doctor.user.get_full_name')
    doctor_specialty = serializers.CharField(source='doctor.bio', read_only=True)
    status_display = serializers.CharField(source='get_status_display')
    
    
    appointment_day = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        
        fields = [
            'id', 
            'doctor_name', 
            'doctor_specialty', 
            'appointment_date', 
            'appointment_time',
            'appointment_day', # اسم اليوم
            'status',
            'status_display'
        ]

    def get_appointment_day(self, obj):
        """
        هذه الدالة تقوم بحساب اسم اليوم من تاريخ الموعد وترجمته للعربية.
        """
        if obj.appointment_date:
            english_day = obj.appointment_date.strftime('%A') # e.g., 'Thursday'
            return DAYS_AR.get(english_day, english_day) # Returns Arabic name, or English if not found
        return None
    
class DoctorAppointmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        # هنا الحقول فقط التي نسمح للطبيب بتعديلها
        fields = ['appointment_date', 'appointment_time']   

class AppointmentRespondSerializer(serializers.Serializer):
    """
    Serializer بسيط جداً يستقبل فقط قيمة بوليانية للقبول أو الرفض.
    """
    accepted = serializers.BooleanField(required=True)

# --- NEW: Serializer for Doctor's Confirmed Bookings List ---
class DoctorBookingsSerializer(serializers.ModelSerializer):
    """
    Serializer مخصص لعرض قائمة الحجوزات المؤكدة للطبيب.
    """
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)

    class Meta:
        model = Appointment
        # نعرض فقط الحقول المطلوبة في الواجهة
        fields = ['id', 'patient_name', 'appointment_date', 'appointment_time']


class FavoriteDoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    favorites_count = serializers.SerializerMethodField()
    class Meta:
        model = DoctorProfile
        fields = ['id', 'full_name', 'address', 'phone_number', 'favorites_count']
    def get_favorites_count(self, obj):
        return obj.favorited_by_patients.count()

class FavoriteDoctorSerializer(serializers.ModelSerializer):
    doctor = FavoriteDoctorListSerializer(read_only=True)
    class Meta:
        model = FavoriteDoctor
        fields = ['id', 'doctor']


class DoctorProfileListSerializer(serializers.ModelSerializer):
    """
    Serializer لعرض قائمة الأطباء للمرضى.
    تم تعديله ليعرض الاسم الكامل وحقل المؤهلات (bio).
    """
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = DoctorProfile
        fields = [
            'id', 
            'full_name', 
            'bio', # هذا هو التخصص الذي سيظهر للمريض
            'address', 
            'phone_number',
            'is_available', 
            'average_rating'
        ]