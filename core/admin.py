# core/admin.py

from django.contrib import admin
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote, Attachment # تم إضافة Attachment

admin.site.register(PatientProfile)
admin.site.register(BloodGlucoseReading)
admin.site.register(Medication)
admin.site.register(DoctorNote)
admin.site.register(Attachment) # <--- تم إضافة هذا السطر