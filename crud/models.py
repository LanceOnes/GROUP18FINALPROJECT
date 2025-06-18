from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.hashers import make_password

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[
        ('teacher', 'Teacher'),
        ('student', 'Student')
    ])
    gender = models.CharField(max_length=10, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ])
    contact_number = models.CharField(max_length=15)
    id_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"

class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Class(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    section = models.CharField(max_length=20)
    room = models.CharField(max_length=20)
    
    class Meta:
        verbose_name_plural = "Classes"
        unique_together = ['subject', 'section']
    
    def __str__(self):
        return f"{self.subject.name} - {self.section}"

class Student(models.Model):
    student_id = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ])
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students', null=True, blank=True)
    teacher = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='teacher_students')

    class Meta:
        # Make student_id unique only within a teacher's scope
        unique_together = ['student_id', 'teacher']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class ClassEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')

    class Meta:
        unique_together = ['student', 'class_instance']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_instance}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time_in = models.TimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    
    class Meta:
        unique_together = ['student', 'class_instance', 'date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_instance} - {self.date}"

class Teacher(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    contact = models.CharField(max_length=15)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # Will be hashed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Hash the password if it's not already hashed
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"