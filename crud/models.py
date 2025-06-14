from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('teacher', 'Teacher'), ('student', 'Student')])
    gender = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=15)
    id_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"

class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Class(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='classes')
    teacher = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='teaching_classes')
    section = models.CharField(max_length=20)
    schedule = models.CharField(max_length=100)
    room = models.CharField(max_length=50)
    
    class Meta:
        verbose_name_plural = 'Classes'
        unique_together = ['subject', 'section']
    
    def __str__(self):
        return f"{self.subject.code} {self.section}"

class ClassEnrollment(models.Model):
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='enrolled_classes')
    enrollment_date = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = ['class_instance', 'student']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.class_instance}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time_in = models.TimeField(default=timezone.now)
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    
    class Meta:
        unique_together = ['student', 'class_instance', 'date']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.class_instance} - {self.date}"

