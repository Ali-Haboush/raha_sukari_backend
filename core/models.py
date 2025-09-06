# core/models.py

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from django.utils import timezone

# --- دوال المسارات تبقى كما هي ---
def patient_profile_picture_path(instance, filename):
    return f'profile_pics/patient_{instance.user.id}/{filename}'

def doctor_profile_picture_path(instance, filename):
    return f'profile_pics/doctor_{instance.user.id}/{filename}'

def attachment_file_path(instance, filename):
    return f'attachments/patient_{instance.patient.id}/{filename}'


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctorprofile')
    specialty = models.CharField(max_length=255, verbose_name="التخصص")
    address = models.CharField(max_length=255, verbose_name="العنوان")
    phone_number = models.CharField(max_length=20, verbose_name="رقم الهاتف")
    bio = models.TextField(blank=True, null=True, verbose_name="نبذة عن الطبيب")
    working_hours = models.TextField(blank=True, null=True, verbose_name="ساعات العمل")
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, verbose_name="متوسط التقييم")
    is_available = models.BooleanField(default=True, verbose_name="متاح الآن")

    patients = models.ManyToManyField('PatientProfile', related_name='doctors', blank=True)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} - {self.specialty}"

class FavoriteDoctor(models.Model):
    patient = models.ForeignKey('PatientProfile', on_delete=models.CASCADE, related_name='favorite_doctors')
    doctor = models.ForeignKey('DoctorProfile', on_delete=models.CASCADE, related_name='favorited_by_patients')
    class Meta:
        unique_together = ('patient', 'doctor')
        verbose_name = "طبيب مفضل"
        verbose_name_plural = "الأطباء المفضلون"
    def __str__(self):
        return f"Patient {self.patient.user.username} favorited Dr. {self.doctor.user.username}"


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patientprofile')
    address = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    diabetes_type = models.CharField(max_length=50, blank=True, null=True)
    diagnosis_date = models.DateField(blank=True, null=True)
    medical_notes = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to=patient_profile_picture_path, blank=True, null=True)
    def __str__(self):
        return f"Patient Profile for {self.user.username}"

@receiver(post_save, sender=User)
def create_or_update_patient_profile(sender, instance, created, **kwargs):
    if not instance.is_staff and not hasattr(instance, 'patientprofile'):
        PatientProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def create_or_update_doctor_profile(sender, instance, created, **kwargs):
    if instance.is_staff and not hasattr(instance, 'doctorprofile'):
        DoctorProfile.objects.create(user=instance)

class BloodGlucoseReading(models.Model):
    READING_TYPE_CHOICES = [
        ('Fasting', 'صائم'),
        ('After Meal', 'بعد الأكل'),
        ('Random', 'عشوائي'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='glucose_readings')
    reading_value = models.FloatField()
    reading_timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    reading_type = models.CharField(max_length=20, choices=READING_TYPE_CHOICES, default='Random', verbose_name="نوع القراءة")
    def __str__(self):
        return f"Glucose Reading for {self.patient.user.username}: {self.reading_value} at {self.reading_timestamp}"

class Medication(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"Medication for {self.patient.user.username}: {self.name}"

class DoctorNote(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='doctor_notes')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_written_notes')
    note_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Note for {self.patient.user.username} by Dr. {self.doctor.first_name} {self.doctor.last_name} on {self.timestamp.date()}"

class Attachment(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=attachment_file_path)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Attachment for {self.patient.user.username}: {self.file.name}"
    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)

class Consultation(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='consultations')
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='doctor_consultations')
    consultation_date = models.DateField()
    consultation_time = models.TimeField()
    diagnosis = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-consultation_date', '-consultation_time']
    def __str__(self):
        return f"Consultation for {self.patient.user.username} by Dr. {self.doctor.first_name if self.doctor else 'N/A'} on {self.consultation_date}"

class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('Medication', 'تذكير دواء'),
        ('Measurement', 'تذكير قياس'),
        ('General', 'تذكير عام'),
    ]
    RECURRENCE_CHOICES = [
        ('Once', 'مرة واحدة'),
        ('Daily', 'يومياً'),
        ('Weekly', 'أسبوعياً'),
    ]
    
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='alerts', verbose_name="المريض")
    name = models.CharField(max_length=100, verbose_name="اسم التنبيه")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES, default='General', verbose_name="نوع التنبيه")
    alert_date = models.DateField(verbose_name="تاريخ التنبيه")
    alert_time = models.TimeField(verbose_name="وقت التنبيه")
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='Once', verbose_name="التكرار")
    is_active = models.BooleanField(default=True, verbose_name="مفعل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإنشاء")
    
    class Meta:
        ordering = ['alert_date', 'alert_time']
        verbose_name = "تنبيه"
        verbose_name_plural = "التنبيهات"

    def __str__(self):
        return f"Alert '{self.name}' for {self.patient.user.username} at {self.alert_time}"

class Appointment(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    STATUS_CHOICES = [
        ('Pending', 'قيد الانتظار'),
        ('Confirmed', 'مقبول'),
        ('Rejected', 'مرفوض'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    notes = models.TextField(blank=True, null=True)
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        verbose_name = "موعد"
        verbose_name_plural = "المواعيد"
    def __str__(self):
        return f"Appointment for {self.patient.user.username} with Dr. {self.doctor.user.username} on {self.appointment_date}"

# --- NEW: Notification Model ---
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="المستلم")
    message = models.TextField(verbose_name="نص الإشعار")
    is_read = models.BooleanField(default=False, verbose_name="تمت القراءة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإشعار")
    
    # حقول اختيارية للربط مع العنصر الذي سبب الإشعار (مثل موعد جديد)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:30]}"
