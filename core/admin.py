# core/admin.py

from django.contrib import admin
from .models import PatientProfile, BloodGlucoseReading, Medication, DoctorNote

# تسجيل النماذج في لوحة الإدارة لعرضها والتحكم بها
admin.site.register(PatientProfile)
admin.site.register(BloodGlucoseReading)
admin.site.register(Medication)
admin.site.register(DoctorNote)