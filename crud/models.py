from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Genders(models.Model):
    class Meta:
        db_table = 'tbl_genders'

    gender_id = models.BigAutoField(primary_key=True, blank=False) 
    gender = models.CharField(max_length=56, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Student(models.Model):
    class Meta: 
        db_table = "tbl_students"
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)  
    last_name = models.CharField(max_length=50)
    gender = models.ForeignKey(Genders, on_delete=models.CASCADE)
    birth_date = models.DateField(blank=False)
    address = models.CharField(max_length=255, blank=False)
    contact_number = models.CharField(max_length=15, unique=True) 
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    enrollment_year = models.IntegerField()
    password = models.CharField(max_length=255, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Teacher(models.Model):
    class Meta:
        db_table = "tbl_teachers"
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50)
    gender = models.ForeignKey(Genders, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=False)
    contact_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    password = models.CharField(max_length=255, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )

    user= models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Course(models.Model):
    class Meta:
        db_table = "tbl_courses"
    name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20, unique=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

class Enrollment(models.Model):
    class Meta:
        db_table = "tbl_enrollments"
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=20)  # e.g., "2023-2024"
    semester = models.CharField(max_length=10)

    class Meta:
        unique_together = ('student', 'course', 'academic_year', 'semester')

    def __str__(self):
        return f"{self.student} in {self.course} ({self.academic_year} {self.semester})"

class Attendance(models.Model):
    class Meta:
        db_table = "tbl_attendance"
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late'), ('Excused', 'Excused')]
    )

    def __str__(self):
        return f"{self.date} - {self.student} - {self.status}"

class Grade(models.Model):
    class Meta:
        db_table = "tbl_grades"
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=10)
    assessment_type = models.CharField(max_length=50)  # e.g., Midterm, Final, Quiz
    score = models.FloatField()

    class Meta:
        unique_together = ('student', 'course', 'academic_year', 'semester', 'assessment_type')

    def __str__(self):
        return f"{self.student} - {self.course} - {self.assessment_type}: {self.score}"