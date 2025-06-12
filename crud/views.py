from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import time
from .forms import LoginForm, SignUpForm
from .models import UserProfile, Attendance, Subject, Class, ClassEnrollment
import csv
import uuid
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

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
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            contact_number = request.POST.get('contact_number')
            subject_code = request.POST.get('subject_code')
            subject_name = request.POST.get('subject_name')
            section = request.POST.get('section')
            schedule = request.POST.get('schedule')
            room = request.POST.get('room', 'Default Room')  # Adding room field

            # Validate passwords match
            if password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'layout/signup.html', {'form_data': request.POST})
            
            # Check if username exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different username.')
                return render(request, 'layout/signup.html', {'form_data': request.POST})

            # Check if email exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists. Please use a different email address.')
                return render(request, 'layout/signup.html', {'form_data': request.POST})

            # Check if subject code exists
            if Subject.objects.filter(code=subject_code).exists():
                messages.error(request, 'Subject code already exists. Please use a different code.')
                return render(request, 'layout/signup.html', {'form_data': request.POST})
            
            # Create User account
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create UserProfile for teacher
            UserProfile.objects.create(
                user=user,
                role='teacher',
                gender='',  # Can be updated later
                contact_number=contact_number
            )
            
            # Create Subject and Class
            subject = Subject.objects.create(
                code=subject_code,
                name=subject_name
            )
            
            Class.objects.create(
                subject=subject,
                teacher=user.userprofile,
                section=section,
                schedule=schedule,
                room=room  # Adding room field
            )
            
            messages.success(request, 'Account created successfully! Please login to continue.')
            return redirect('login')
            
        except Exception as e:
            # Clean up if something goes wrong
            if 'user' in locals():
                user.delete()
            
            error_message = str(e)
            if 'username' in error_message.lower():
                messages.error(request, 'Username already exists. Please choose a different username.')
            elif 'email' in error_message.lower():
                messages.error(request, 'Email already exists. Please use a different email address.')
            elif 'subject' in error_message.lower():
                messages.error(request, 'Subject code already exists. Please use a different code.')
            else:
                messages.error(request, f'An error occurred: {str(e)}')
            
            return render(request, 'layout/signup.html', {'form_data': request.POST})
    
    return render(request, 'layout/signup.html', {})

def logout_view(request):
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('login')

@login_required
def take_attendance(request):
    """View for taking attendance for a class."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get teacher's classes with subject information
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    selected_class = request.GET.get('class')
    enrollments = []

    if selected_class:
        try:
            # Verify the class belongs to the teacher
            class_obj = teacher_classes.get(id=selected_class)
            # Get all enrollments for the class
            enrollments = ClassEnrollment.objects.filter(class_instance=class_obj).select_related('student__user')

            if request.method == 'POST':
                date = request.POST.get('date')
                if not date:
                    messages.error(request, 'Date is required')
                    return redirect('take_attendance')

                success_count = 0
                error_count = 0
                
                # Process each student's attendance
                for enrollment in enrollments:
                    student_id = enrollment.student.id
                    status = request.POST.get(f'status_{student_id}')
                    time_in = request.POST.get(f'time_{student_id}')
                    notes = request.POST.get(f'notes_{student_id}', '')

                    try:
                        # Create or update attendance record
                        attendance, created = Attendance.objects.update_or_create(
                            student=enrollment.student,
                            class_instance=class_obj,
                            date=date,
                            defaults={
                                'status': status,
                                'time_in': time_in,
                                'notes': notes
                            }
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        messages.error(request, f'Error recording attendance for {enrollment.student.user.get_full_name()}: {str(e)}')

                if success_count > 0:
                    messages.success(request, f'Successfully recorded attendance for {success_count} student(s).')
                if error_count > 0:
                    messages.warning(request, f'Failed to record attendance for {error_count} student(s).')
                
                return redirect('manage_attendance')

        except Class.DoesNotExist:
            messages.error(request, 'Invalid class selected.')
            return redirect('take_attendance')
        except Exception as e:
            messages.error(request, f'Error recording attendance: {str(e)}')

    context = {
        'classes': teacher_classes,
        'selected_class': selected_class,
        'enrollments': enrollments,
        'page_title': 'Take Attendance'
    }

    return render(request, 'teachers/take_attendance.html', context)

@login_required
def teacher_dashboard(request):
    # Check if user has a profile
    if not hasattr(request.user, 'userprofile'):
        # Create a default profile if it doesn't exist
        UserProfile.objects.create(
            user=request.user,
            role='teacher',
            gender='',
            contact_number=''
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
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get filter parameters
    date_filter = request.GET.get('date')
    status_filter = request.GET.get('status')
    class_filter = request.GET.get('class')
    
    # Base queryset - filter by teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).values_list('id', flat=True)
    attendance_list = Attendance.objects.select_related(
        'student__user', 
        'class_instance__subject'
    ).filter(class_instance__in=teacher_classes).order_by('-date', '-time_in')
    
    # Apply filters
    if date_filter:
        attendance_list = attendance_list.filter(date=date_filter)
    if status_filter:
        attendance_list = attendance_list.filter(status=status_filter)
    if class_filter:
        attendance_list = attendance_list.filter(class_instance_id=class_filter)
    
    # Get only this teacher's classes for the filter dropdown
    classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    # Pagination
    paginator = Paginator(attendance_list, 10)
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
    if request.method == 'POST':
        subject_code = request.POST.get('subject_code')
        subject_name = request.POST.get('subject_name')
        section = request.POST.get('section')
        schedule = request.POST.get('schedule')
        room = request.POST.get('room', 'Default Room')  # Adding room with default value
        
        try:
            # Get or create the subject
            subject, created = Subject.objects.get_or_create(
                code=subject_code,
                defaults={'name': subject_name}
            )
            
            # Check if class with this subject and section already exists
            if Class.objects.filter(subject=subject, section=section).exists():
                messages.error(request, f'A class with subject {subject_code} and section {section} already exists.')
            else:
                # Create the class
                Class.objects.create(
                    subject=subject,
                    teacher=request.user.userprofile,
                    section=section,
                    schedule=schedule,
                    room=room  # Adding room field
                )
                messages.success(request, 'Class created successfully!')
            
            return redirect('add_class')
            
        except Exception as e:
            if 'crud_class_subject_id_section' in str(e):
                messages.error(request, f'A class with subject {subject_code} and section {section} already exists.')
            else:
                messages.error(request, 'An error occurred while creating the class. Please try again.')
    
    # Get all classes for the current teacher
    classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    return render(request, 'teachers/add_class.html', {
        'classes': classes,
        'page_title': 'Manage Classes'
    })

@login_required
def edit_class(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id, teacher=request.user.userprofile)
    
    if request.method == 'POST':
        try:
            # Update subject
            subject = class_obj.subject
            subject.code = request.POST.get('subject_code')
            subject.name = request.POST.get('subject_name')
            subject.save()
            
            # Update class
            class_obj.section = request.POST.get('section')
            class_obj.schedule = request.POST.get('schedule')
            class_obj.room = request.POST.get('room')
            class_obj.save()
            
            messages.success(request, 'Class updated successfully!')
            return redirect('add_class')
            
        except Exception as e:
            messages.error(request, str(e))
    
    return render(request, 'teachers/edit_class.html', {
        'class': class_obj,
        'page_title': 'Edit Class'
    })

@login_required
def delete_class(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id, teacher=request.user.userprofile)
    
    try:
        # This will also delete related enrollments due to CASCADE
        class_obj.delete()
        messages.success(request, 'Class deleted successfully!')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('add_class')

@login_required
def student_list(request):
    """View for listing students."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get the selected class filter
    selected_class = request.GET.get('class')
    
    # Get teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    # Get students based on filter
    if selected_class:
        try:
            # Verify the class belongs to the teacher
            class_obj = teacher_classes.get(id=selected_class)
            # Get students enrolled in the selected class
            student_ids = ClassEnrollment.objects.filter(
                class_instance=class_obj
            ).values_list('student_id', flat=True)
            students = UserProfile.objects.filter(
                id__in=student_ids,
                role='student'
            ).select_related('user')
        except Class.DoesNotExist:
            messages.error(request, 'Invalid class selected.')
            students = UserProfile.objects.none()
    else:
        # Get all students enrolled in any of teacher's classes
        student_ids = ClassEnrollment.objects.filter(
            class_instance__teacher=request.user.userprofile
        ).values_list('student_id', flat=True)
        students = UserProfile.objects.filter(
            id__in=student_ids,
            role='student'
        ).select_related('user')

    # Set up pagination
    paginator = Paginator(students, 10)  # Show 10 students per page
    page = request.GET.get('page')
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    context = {
        'students': students,
        'total_students': paginator.count,
        'classes': teacher_classes,
        'selected_class': int(selected_class) if selected_class else None,
        'page_title': 'Students'
    }
    return render(request, 'teachers/students.html', context)

@login_required
def add_student(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = str(uuid.uuid4())  # Generate a random password
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            gender = request.POST.get('gender')
            contact_number = request.POST.get('contact_number')
            class_id = request.POST.get('classes')

            # Validate class selection
            if not class_id:
                messages.error(request, 'Please select a class.')
                return render(request, 'teachers/add_student.html', {
                    'classes': Class.objects.filter(teacher=request.user.userprofile),
                    'form_data': request.POST,
                    'page_title': 'Add Student'
                })

            # Verify the class belongs to the teacher
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user.userprofile)
            except Class.DoesNotExist:
                messages.error(request, 'Invalid class selection. Please select a valid class.')
                return render(request, 'teachers/add_student.html', {
                    'classes': Class.objects.filter(teacher=request.user.userprofile),
                    'form_data': request.POST,
                    'page_title': 'Add Student'
                })

            # Get all students in teacher's classes
            teacher_classes = Class.objects.filter(teacher=request.user.userprofile)
            enrolled_students = ClassEnrollment.objects.filter(
                class_instance__in=teacher_classes
            ).values_list('student', flat=True)

            # Check if username exists in teacher's students
            username_exists = UserProfile.objects.filter(
                id__in=enrolled_students,
                user__username=username
            ).exists()

            if username_exists:
                messages.error(request, 'A student with this username already exists in your classes.')
                return render(request, 'teachers/add_student.html', {
                    'classes': Class.objects.filter(teacher=request.user.userprofile),
                    'form_data': request.POST,
                    'page_title': 'Add Student'
                })

            # Check if email exists in teacher's students
            email_exists = UserProfile.objects.filter(
                id__in=enrolled_students,
                user__email=email
            ).exists()

            if email_exists:
                messages.error(request, 'A student with this email already exists in your classes.')
                return render(request, 'teachers/add_student.html', {
                    'classes': Class.objects.filter(teacher=request.user.userprofile),
                    'form_data': request.POST,
                    'page_title': 'Add Student'
                })

            # Create user account
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Create student profile
            student = UserProfile.objects.create(
                user=user,
                role='student',
                gender=gender,
                contact_number=contact_number
            )

            # Create class enrollment
            ClassEnrollment.objects.create(
                student=student,
                class_instance=class_obj
            )

            messages.success(request, 'Student added successfully!')
            return redirect('student_list')

        except Exception as e:
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error adding student: {str(e)}')

    # Get only this teacher's classes
    classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    return render(request, 'teachers/add_student.html', {
        'classes': classes,
        'page_title': 'Add Student'
    })

@login_required
def edit_student(request, student_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get student only if enrolled in teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile)
    enrolled_students = ClassEnrollment.objects.filter(class_instance__in=teacher_classes).values_list('student', flat=True)
    student = get_object_or_404(UserProfile, id=student_id, id__in=enrolled_students)
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            gender = request.POST.get('gender')
            contact_number = request.POST.get('contact_number')
            class_id = request.POST.get('class')

            # Verify the class belongs to the teacher
            class_obj = get_object_or_404(Class, id=class_id, teacher=request.user.userprofile)

            # Check if username exists in any of teacher's students (excluding current student)
            username_exists = UserProfile.objects.filter(
                id__in=enrolled_students,  # Only check among teacher's students
                user__username=username
            ).exclude(id=student.id).exists()

            if username_exists:
                messages.error(request, 'A student with this username already exists in your classes.')
                return render(request, 'teachers/edit_student.html', {
                    'student': student,
                    'classes': teacher_classes,
                    'current_class': student.enrolled_classes.filter(class_instance__teacher=request.user.userprofile).first(),
                    'page_title': 'Edit Student'
                })

            # Check if email exists in any of teacher's students (excluding current student)
            email_exists = UserProfile.objects.filter(
                id__in=enrolled_students,  # Only check among teacher's students
                user__email=email
            ).exclude(id=student.id).exists()

            if email_exists:
                messages.error(request, 'A student with this email already exists in your classes.')
                return render(request, 'teachers/edit_student.html', {
                    'student': student,
                    'classes': teacher_classes,
                    'current_class': student.enrolled_classes.filter(class_instance__teacher=request.user.userprofile).first(),
                    'page_title': 'Edit Student'
                })

            # Update user info
            student.user.username = username
            student.user.first_name = first_name
            student.user.last_name = last_name
            student.user.email = email
            student.user.save()

            # Update profile info
            student.gender = gender
            student.contact_number = contact_number
            student.save()

            # Update class enrollment
            enrollment = ClassEnrollment.objects.filter(student=student, class_instance__teacher=request.user.userprofile).first()
            if enrollment:
                enrollment.class_instance = class_obj
                enrollment.save()
            else:
                ClassEnrollment.objects.create(student=student, class_instance=class_obj)

            messages.success(request, 'Student updated successfully!')
            return redirect('student_list')

        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')

    context = {
        'student': student,
        'classes': teacher_classes,
        'current_class': student.enrolled_classes.filter(class_instance__teacher=request.user.userprofile).first(),
        'page_title': 'Edit Student'
    }
    return render(request, 'teachers/edit_student.html', context)

@login_required
def delete_student(request, student_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get student only if enrolled in teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile)
    enrolled_students = ClassEnrollment.objects.filter(class_instance__in=teacher_classes).values_list('student', flat=True)
    student = get_object_or_404(UserProfile, id=student_id, id__in=enrolled_students)

    try:
        # Delete user (this will cascade delete the profile and enrollments)
        student.user.delete()
        messages.success(request, 'Student deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting student: {str(e)}')
    
    return redirect('student_list')

@login_required
def teacher_class_detail(request, class_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get class only if it belongs to the teacher
    class_obj = get_object_or_404(Class, id=class_id, teacher=request.user.userprofile)
    enrolled_students = ClassEnrollment.objects.filter(class_instance=class_obj).select_related('student__user')

    context = {
        'class': class_obj,
        'enrolled_students': enrolled_students,
        'page_title': f'Class Detail - {class_obj}'
    }

    return render(request, 'teachers/class_detail.html', context)

@login_required
def get_students(request, class_id):
    """AJAX endpoint to get students in a class."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Verify the class belongs to the teacher
        class_obj = Class.objects.get(id=class_id, teacher=request.user.userprofile)
        
        # Get all enrollments for the class
        enrollments = ClassEnrollment.objects.filter(class_instance=class_obj).select_related('student__user')
        
        students = [{
            'id': enrollment.student.id,
            'name': enrollment.student.user.get_full_name(),
            'email': enrollment.student.user.email
        } for enrollment in enrollments]
        
        return JsonResponse(students, safe=False)
        
    except Class.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def delete_attendance(request, record_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get attendance record only if it belongs to teacher's class
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).values_list('id', flat=True)
    attendance = get_object_or_404(Attendance, id=record_id, class_instance_id__in=teacher_classes)

    try:
        attendance.delete()
        messages.success(request, 'Attendance record deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting attendance record: {str(e)}')

    return redirect('manage_attendance')

@login_required
def edit_attendance(request, record_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get attendance record only if it belongs to teacher's class
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).values_list('id', flat=True)
    attendance = get_object_or_404(Attendance, id=record_id, class_instance_id__in=teacher_classes)

    if request.method == 'POST':
        try:
            # Update attendance record
            attendance.status = request.POST.get('status')
            attendance.time_in = request.POST.get('time_in')
            attendance.notes = request.POST.get('notes', '')
            attendance.save()
            messages.success(request, 'Attendance record updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating attendance: {str(e)}')
        return redirect('manage_attendance')

    context = {
        'attendance': attendance,
        'page_title': 'Edit Attendance'
    }
    return render(request, 'teachers/edit_attendance.html', context)

