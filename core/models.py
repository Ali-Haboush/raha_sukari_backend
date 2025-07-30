# core/models.py

from django.db import models
from django.contrib.auth.models import User

# 1. نموذج PatientProfile (معلومات إضافية عن المريض)
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    age = models.IntegerField(null=True, blank=True, verbose_name="العمر")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="الوزن (كجم)")
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="الطول (سم)")

    DIABETES_TYPE_CHOICES = [
        ('Type 1', 'النوع الأول'),
        ('Type 2', 'النوع الثاني'),
        ('Gestational', 'سكري الحمل'),
        ('Other', 'أخرى'),
    ]
    diabetes_type = models.CharField(max_length=20, choices=DIABETES_TYPE_CHOICES, default='Type 2', verbose_name="نوع السكري")
    diagnosis_date = models.DateField(null=True, blank=True, verbose_name="تاريخ التشخيص")

    address = models.CharField(max_length=255, null=True, blank=True, verbose_name="العنوان")
    GENDER_CHOICES = [
        ('Male', 'ذكر'),
        ('Female', 'أنثى'),
        ('Other', 'أخرى'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True, verbose_name="الجنس")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="تاريخ الميلاد")
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="رقم الهاتف")
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, verbose_name="الصورة الشخصية")
    medical_notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات طبية للطبيب")

    def __str__(self):
        return f"ملف تعريف لـ {self.user.username}"

    class Meta:
        verbose_name = "ملف تعريف المريض"
        verbose_name_plural = "ملفات تعريف المرضى"

# 2. نموذج BloodGlucoseReading (قراءات السكر)
class BloodGlucoseReading(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='glucose_readings', verbose_name="المريض")
    value = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="قيمة السكر")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت")

    READING_TYPE_CHOICES = [
        ('Before Meal', 'قبل الوجبة'),
        ('After Meal', 'بعد الوجبة'),
        ('Fasting', 'صائم'),
        ('Before Sleep', 'قبل النوم'),
        ('Other', 'أخرى'),
    ]
    reading_type = models.CharField(max_length=20, choices=READING_TYPE_CHOICES, default='Other', verbose_name="نوع القياس")
    notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات")

    def __str__(self):
        return f"قراءة سكر {self.value} لـ {self.patient.user.username} بتاريخ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "قراءة سكر"
        verbose_name_plural = "قراءات السكر"
        ordering = ['-timestamp']


# 3. نموذج Medication (الأدوية)
class Medication(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medications', verbose_name="المريض")
    name = models.CharField(max_length=100, verbose_name="اسم الدواء")
    dosage = models.CharField(max_length=50, null=True, blank=True, verbose_name="الجرعة")

    ADMINISTRATION_CHOICES = [
        ('Oral', 'فموي'),
        ('Injection', 'حقن'),
        ('Topical', 'موضعي'),
        ('Other', 'أخرى'),
    ]
    administration_method = models.CharField(max_length=20, choices=ADMINISTRATION_CHOICES, default='Oral', verbose_name="طريقة الاستخدام")
    start_date = models.DateField(null=True, blank=True, verbose_name="تاريخ البدء")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الانتهاء")
    notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات")

    def __str__(self):
        return f"دواء {self.name} لـ {self.patient.user.username}"

    class Meta:
        verbose_name = "دواء"
        verbose_name_plural = "الأدوية"

# 4. نموذج DoctorNote (ملاحظات الطبيب)
class DoctorNote(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='doctor_notes', verbose_name="المريض")
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الطبيب")
    note_text = models.TextField(verbose_name="نص الملاحظة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت")

    def __str__(self):
        doctor_name = self.doctor.username if self.doctor else "غير معروف"
        return f"ملاحظة للطبيب {doctor_name} لـ {self.patient.user.username} بتاريخ {self.timestamp.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "ملاحظة طبيب"
        verbose_name_plural = "ملاحظات الأطباء"
        ordering = ['-timestamp']

# <--- نموذج جديد: Attachment (المرفقات)
class Attachment(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='attachments', verbose_name="المريض")
    # FileField يمكن أن يخزن أي نوع من الملفات. 'attachments/' هو المجلد الفرعي داخل MEDIA_ROOT
    file = models.FileField(upload_to='attachments/', verbose_name="الملف")
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="الوصف")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")

    def __str__(self):
        return f"مرفق لـ {self.patient.user.username} - {self.file.name.split('/')[-1]}" # عرض اسم الملف فقط

    class Meta:
        verbose_name = "مرفق"
        verbose_name_plural = "المرفقات"
        ordering = ['-uploaded_at']
# --- نهاية نموذج Attachment ---