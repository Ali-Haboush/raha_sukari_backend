# core/admin.py

from django.contrib import admin
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote, Attachment, Consultation, Alert # تم إضافة Alert

# تسجيل PatientProfile في لوحة الإدارة
@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'date_of_birth', 'phone_number', 'diabetes_type', 'diagnosis_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone_number')
    list_filter = ('gender', 'diabetes_type')
    raw_id_fields = ('user',)

# تسجيل BloodGlucoseReading في لوحة الإدارة
@admin.register(BloodGlucoseReading)
class BloodGlucoseReadingAdmin(admin.ModelAdmin):
    list_display = ('patient', 'reading_value', 'reading_timestamp')
    search_fields = ('patient__user__username',)
    list_filter = ('reading_timestamp',)
    raw_id_fields = ('patient',)

# تسجيل Medication في لوحة الإدارة
@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'name', 'dosage', 'frequency', 'start_date', 'end_date')
    search_fields = ('patient__user__username', 'name')
    list_filter = ('start_date', 'end_date')
    raw_id_fields = ('patient',)

# تسجيل DoctorNote في لوحة الإدارة
@admin.register(DoctorNote)
class DoctorNoteAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'timestamp', 'note_text')
    search_fields = ('patient__user__username', 'doctor__username', 'note_text')
    list_filter = ('timestamp',)
    raw_id_fields = ('patient', 'doctor')

# تسجيل Attachment في لوحة الإدارة
@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'file', 'description', 'uploaded_at')
    search_fields = ('patient__user__username', 'description')
    list_filter = ('uploaded_at',)
    raw_id_fields = ('patient',)

# تسجيل Consultation في لوحة الإدارة
@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'consultation_date', 'consultation_time', 'diagnosis')
    search_fields = ('patient__user__username', 'doctor__username', 'diagnosis', 'treatment')
    list_filter = ('consultation_date', 'doctor')
    raw_id_fields = ('patient', 'doctor')

# --- NEW: تسجيل Alert في لوحة الإدارة ---
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'alert_type', 'message', 'is_read', 'timestamp', 'sender_user')
    search_fields = ('patient__user__username', 'alert_type', 'message')
    list_filter = ('alert_type', 'is_read', 'timestamp')
    raw_id_fields = ('patient', 'sender_user', 'related_reading')
# --- نهاية Alert Admin ---