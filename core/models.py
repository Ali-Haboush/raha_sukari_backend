# core/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from django.utils import timezone # تم إضافة هذا الاستيراد

# دالة لمسار حفظ الصورة الشخصية
def patient_profile_picture_path(instance, filename):
    return f'profile_pics/user_{instance.user.id}/{filename}'

# دالة لمسار حفظ المرفقات
def attachment_file_path(instance, filename):
    return f'attachments/patient_{instance.patient.id}/{filename}'

# --- PatientProfile Model ---
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

# Signal لإنشاء PatientProfile تلقائياً عند إنشاء User جديد
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        PatientProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.patientprofile.save()

# --- BloodGlucoseReading Model ---
class BloodGlucoseReading(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='glucose_readings')
    reading_value = models.FloatField()
    reading_timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Glucose Reading for {self.patient.user.username}: {self.reading_value} at {self.reading_timestamp}"

# --- Medication Model ---
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

# --- DoctorNote Model ---
class DoctorNote(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='doctor_notes')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_written_notes')
    note_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.patient.user.username} by Dr. {self.doctor.first_name} {self.doctor.last_name} on {self.timestamp.date()}"

# --- Attachment Model ---
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

# --- Consultation Model ---
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

# --- NEW: Alert (Notification) Model ---
class Alert(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='alerts', verbose_name="المريض")
    # ممكن يرسل من طبيب، أو يكون تنبيه تلقائي، فنخليه اختياري
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المرسل")
    message = models.TextField(verbose_name="نص التنبيه")

    ALERT_TYPE_CHOICES = [
        ('High Sugar', 'ارتفاع السكر'),
        ('Low Sugar', 'انخفاض السكر'),
        ('Missed Medication', 'جرعة دواء مفقودة'),
        ('Appointment Reminder', 'تذكير موعد'),
        ('General', 'عام'),
        ('Doctor Note', 'ملاحظة طبيب جديدة')
    ]
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES, default='General', verbose_name="نوع التنبيه")

    is_read = models.BooleanField(default=False, verbose_name="تمت القراءة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="وقت التنبيه")

    # ربط التنبيه بقراءة سكر معينة لو كان التنبيه بسببها (اختياري)
    related_reading = models.ForeignKey(BloodGlucoseReading, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="قراءة السكر المرتبطة")

    class Meta:
        ordering = ['-timestamp'] # ترتيب التنبيهات من الأحدث للأقدم
        verbose_name = "تنبيه / إشعار"
        verbose_name_plural = "التنبيهات / الإشعارات"

    def __str__(self):
        return f"تنبيه لـ {self.patient.user.username} - {self.get_alert_type_display()} ({'مقروء' if self.is_read else 'غير مقروء'})"
# --- نهاية Alert Model ---