from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import time
from .forms import LoginForm, SignUpForm
from .models import UserProfile, Attendance, Subject, Class
import csv
import uuid
from django.core.paginator import Paginator

def login_view(request):
    if request.user.is_authenticated:
        return redirect('teacher_dashboard')
    
    # Clear any existing messages when rendering the login page
    storage = messages.get_messages(request)
    storage.used = True
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('teacher_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'layout/login.html', {})
                                                                                                                                                                                                        
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('teacher_dashboard')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Create the user with just username and password
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )

            # Create teacher profile with default time values
            UserProfile.objects.create(
                user=user,
                role='teacher',
                gender='',  # Set as empty string by default
                contact_number='',  # Set as empty string by default
                time_in=time(8, 0),  # Default time: 8:00 AM
                time_out=time(17, 0)  # Default time: 5:00 PM
            )

            # Automatically log in the user
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to ScholarTrack.')
            return redirect('teacher_dashboard')
    else:
        form = SignUpForm()

    return render(request, 'layout/signup.html', {
        'form': form,
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('login')



@login_required
def teacher_dashboard(request):
    # Check if user has a profile
    if not hasattr(request.user, 'userprofile'):
        # Create a default profile if it doesn't exist
        UserProfile.objects.create(
            user=request.user,
            role='teacher',
            gender='',
            contact_number='',
            time_in=time(8, 0),  # Default time: 8:00 AM
            time_out=time(17, 0)  # Default time: 5:00 PM
        )
    elif request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')
    
    teacher_profile = request.user.userprofile
    classes = Class.objects.filter(teacher=teacher_profile)
    
    today = timezone.now().date()
    class_stats = []
    
    for class_obj in classes:
        total_students = class_obj.enrollments.count()
        todays_attendance = Attendance.objects.filter(
            class_instance=class_obj,
            date=today
        ).count()
        
        class_stats.append({
            'class': class_obj,
            'total_students': total_students,
            'marked_today': todays_attendance,
            'pending_today': total_students - todays_attendance
        })
    
    context = {
        'class_stats': class_stats,
        'page_title': 'Teacher Dashboard'
    }
    
    return render(request, 'teachers/dashboard.html', context)


@login_required
def manage_attendance(request):
    """View for displaying attendance records."""
    # Get filter parameters
    date_filter = request.GET.get('date')
    status_filter = request.GET.get('status')
    class_filter = request.GET.get('class')
    
    # Base queryset
    attendance_list = Attendance.objects.select_related(
        'student__user', 
        'class_instance__subject'
    ).order_by('-date', '-time_in')
    
    # Apply filters
    if date_filter:
        attendance_list = attendance_list.filter(date=date_filter)
    if status_filter:
        attendance_list = attendance_list.filter(status=status_filter)
    if class_filter:
        attendance_list = attendance_list.filter(class_instance_id=class_filter)
    
    # Get all classes for the filter dropdown
    classes = Class.objects.select_related('subject').all()
    
    # Pagination
    paginator = Paginator(attendance_list, 10)  # Show 10 records per page
    page_number = request.GET.get('page', 1)
    attendance_records = paginator.get_page(page_number)
    
    context = {
        'page_title': 'Manage Attendance',
        'attendance_records': attendance_records,
        'classes': classes,
        'current_date': date_filter,
        'current_status': status_filter,
        'current_class': class_filter,
        'status_choices': Attendance.STATUS_CHOICES,
        'total_records': attendance_list.count()
    }
    
    return render(request, 'teachers/attendance.html', context)

@login_required
def add_class(request):
    """View for adding a new class."""
    if request.method == 'POST':
        try:
            # Get form data
            subject_id = request.POST.get('subject')
            section = request.POST.get('section')
            schedule = request.POST.get('schedule')
            room = request.POST.get('room')

            # Get the subject
            subject = get_object_or_404(Subject, id=subject_id)

            # Create the class
            Class.objects.create(
                subject=subject,
                teacher=request.user.userprofile,
                section=section,
                schedule=schedule,
                room=room
            )

            messages.success(request, 'Class added successfully')
            return redirect('teacher_dashboard')

        except Exception as e:
            messages.error(request, str(e))
            return redirect('add_class')

    # Get all subjects for the dropdown
    subjects = Subject.objects.all().order_by('code')
    
    context = {
        'page_title': 'Add New Class',
        'subjects': subjects
    }
    return render(request, 'teachers/add_class.html', context)

@login_required
def student_list(request):
    """View for displaying the list of students."""
    students_list = UserProfile.objects.filter(role='student')
    
    # Number of students per page
    per_page = 10
    paginator = Paginator(students_list, per_page)
    page_number = request.GET.get('page', 1)
    students = paginator.get_page(page_number)
    
    return render(request, 'teachers/students.html', {
        'students': students,
        'total_students': students_list.count()
    })

@login_required
def add_student(request):
    """View for adding a new student."""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        gender = request.POST.get('gender')
        contact_number = request.POST.get('contact_number')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out')

        try:
            # Create user with a random password
            random_password = str(uuid.uuid4())  # Generate a random password
            user = User.objects.create_user(
                username=username,
                email=email,
                password=random_password,  # Set random password
                first_name=first_name,
                last_name=last_name
            )

            # Create user profile
            UserProfile.objects.create(
                user=user,
                role='student',
                gender=gender,
                contact_number=contact_number,
                time_in=time_in,
                time_out=time_out
            )

            messages.success(request, 'Student added successfully')
            return redirect('student_list')

        except Exception as e:
            messages.error(request, str(e))
            return redirect('add_student')

    return render(request, 'teachers/add_student.html')

@login_required
def edit_student(request, student_id):
    """View for editing an existing student."""
    student = get_object_or_404(UserProfile, id=student_id, role='student')
    context = {'student': student}
    
    if request.method == 'POST':
        try:
            # Update user
            student.user.first_name = request.POST.get('first_name')
            student.user.last_name = request.POST.get('last_name')
            student.user.username = request.POST.get('username')
            student.user.email = request.POST.get('email')
            student.user.save()

            # Update profile
            student.gender = request.POST.get('gender')
            student.contact_number = request.POST.get('contact_number')
            student.time_in = request.POST.get('time_in')
            student.time_out = request.POST.get('time_out')
            student.save()

            messages.success(request, 'Student updated successfully')
            return redirect('student_list')

        except Exception as e:
            messages.error(request, str(e))
            return redirect('edit_student', student_id=student_id)

    return render(request, 'teachers/edit_student.html', context)

@login_required
def delete_student(request, student_id):
    """View for deleting a student."""
    student = get_object_or_404(UserProfile, id=student_id, role='student')
    try:
        student.user.delete()  # This will also delete the UserProfile due to CASCADE
        messages.success(request, 'Student deleted successfully')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('student_list')

@login_required
def attendance_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    attendance_records = Attendance.objects.select_related(
        'student__user',
        'class_instance'
    ).filter(
        student__role='student'
    ).order_by('-date', 'student__user__first_name')
    
    if start_date:
        attendance_records = attendance_records.filter(date__gte=start_date)
    if end_date:
        attendance_records = attendance_records.filter(date__lte=end_date)
    
    context = {
        'attendance_records': attendance_records,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'teachers/attendance_report.html', context)

@login_required
def edit_attendance(request, record_id):
    """View for editing an attendance record."""
    attendance = get_object_or_404(Attendance, id=record_id)
    
    if request.method == 'POST':
        try:
            # Update attendance record
            attendance.date = request.POST.get('date')
            attendance.time_in = request.POST.get('time_in')
            attendance.status = request.POST.get('status')
            attendance.save()

            messages.success(request, 'Attendance record updated successfully')
            return redirect('manage_attendance')

        except Exception as e:
            messages.error(request, str(e))
            return redirect('edit_attendance', record_id=record_id)

    context = {
        'attendance': attendance,
        'status_choices': Attendance.STATUS_CHOICES,
        'page_title': 'Edit Attendance Record'
    }
    return render(request, 'teachers/edit_attendance.html', context)

@login_required
def delete_attendance(request, record_id):
    """View for deleting an attendance record."""
    attendance = get_object_or_404(Attendance, id=record_id)
    try:
        attendance.delete()
        messages.success(request, 'Attendance record deleted successfully')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('manage_attendance')

@login_required
def export_attendance_csv(request):
    """Export attendance records to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_records.csv"'
    
    # Create the CSV writer
    writer = csv.writer(response)
    
    # Write the header row
    writer.writerow(['Student', 'Class', 'Section', 'Date', 'Time In', 'Status'])
    
    # Get all attendance records
    attendance_records = Attendance.objects.select_related(
        'student__user',
        'class_instance__subject'
    ).all()
    
    # Write the data rows
    for record in attendance_records:
        writer.writerow([
            record.student.user.get_full_name(),
            record.class_instance.subject.code,
            record.class_instance.section,
            record.date,
            record.time_in.strftime('%I:%M %p'),
            record.status.title()
        ])
    
    return response

