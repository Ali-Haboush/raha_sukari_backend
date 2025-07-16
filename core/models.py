# core/models.py

from django.db import models
from django.contrib.auth.models import User # لاستخدام نموذج المستخدم الأساسي في Django

# 1. نموذج PatientProfile (معلومات إضافية عن المريض)
class PatientProfile(models.Model):
    # ربط ملف تعريف المريض بنموذج المستخدم الأساسي في Django
    # on_delete=models.CASCADE: لو تم حذف المستخدم، ملف تعريفه بينحذف معاه تلقائياً
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

    def __str__(self):
        return f"ملف تعريف لـ {self.user.username}"

    class Meta:
        verbose_name = "ملف تعريف المريض"
        verbose_name_plural = "ملفات تعريف المرضى"

# 2. نموذج BloodGlucoseReading (قراءات السكر)
class BloodGlucoseReading(models.Model):
    # ربط القراءة بالمريض اللي عملها
    # related_name='glucose_readings': بيسمح لنا نجيب كل قراءات السكر لمريض معين بسهولة (patient.glucose_readings.all())
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='glucose_readings', verbose_name="المريض")
    value = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="قيمة السكر") # مثال: 120.50
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت") # بيتسجل تلقائياً عند إضافة القراءة

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
        ordering = ['-timestamp'] # ترتيب القراءات من الأحدث للأقدم

# 3. نموذج Medication (الأدوية)
class Medication(models.Model):
    # ربط الدواء بالمريض اللي بياخده
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
    # ربط الملاحظة بالمريض المعني والطبيب اللي كتبها
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='doctor_notes', verbose_name="المريض")
    # ممكن نربط الطبيب اللي كتب الملاحظة مباشرة بنموذج User عشان نعرف مين اللي كتب الملاحظة
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الطبيب")
    note_text = models.TextField(verbose_name="نص الملاحظة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت")

    def __str__(self):
        doctor_name = self.doctor.username if self.doctor else "غير معروف"
        return f"ملاحظة للطبيب {doctor_name} لـ {self.patient.user.username} بتاريخ {self.timestamp.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "ملاحظة طبيب"
        verbose_name_plural = "ملاحظات الأطباء"
        ordering = ['-timestamp'] # ترتيب الملاحظات من الأحدث للأقدم