from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import time
from .forms import LoginForm, SignUpForm
from .models import UserProfile, Attendance, Subject, Class, ClassEnrollment, Student
import csv
import uuid
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.db.utils import IntegrityError
from django.db import transaction

def login_view(request):
    if request.user.is_authenticated:
        return redirect('teacher_dashboard')
    
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            if not hasattr(user, 'userprofile'):
                messages.error(request, 'No teacher profile found for this account.')
                return render(request, 'layout/login.html', {'form': form})
            if user.userprofile.role != 'teacher':
                messages.error(request, 'Access denied. Teacher access only.')
                return render(request, 'layout/login.html', {'form': form})
            
            login(request, user)
            return redirect('teacher_dashboard')
    
    return render(request, 'layout/login.html', {'form': form})

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                # Start a database transaction
                with transaction.atomic():
                    username = form.cleaned_data['username']
                    password = form.cleaned_data['password']
                    email = form.cleaned_data['email']
                    first_name = form.cleaned_data['first_name']
                    last_name = form.cleaned_data['last_name']
                    contact_number = form.cleaned_data['contact_number']
                    subject_code = form.cleaned_data['subject_code'].strip()  # Clean whitespace
                    subject_name = form.cleaned_data['subject_name']
                    section = form.cleaned_data['section']
                    room = form.cleaned_data['room']

                    # Create user
                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        email=email,
                        first_name=first_name,
                        last_name=last_name
                    )
                    
                    # Create user profile with teacher role
                    user_profile = UserProfile.objects.create(
                        user=user,
                        role='teacher',
                        gender='',  
                        contact_number=contact_number,
                        id_number=f"T{timezone.now().strftime('%y%m%d%H%M%S')}"  # Generate teacher ID
                    )
                    
                    # Create subject
                    subject = Subject.objects.create(
                        code=subject_code,
                        name=subject_name
                    )
                    
                    # Create class
                    Class.objects.create(
                        subject=subject,
                        teacher=user_profile,
                        section=section,
                        room=room
                    )
                    messages.success(request, '🎉 Account created successfully! Please log in to continue.')
                    return redirect('login')
            except IntegrityError as e:
                # Handle database integrity errors (like duplicate entries)
                if 'unique constraint' in str(e).lower() or 'duplicate entry' in str(e).lower():
                    if 'username' in str(e).lower():
                        form.add_error('username', 'Username already exists.')
                    elif 'email' in str(e).lower():
                        form.add_error('email', 'Email already exists.')
                    elif 'subject' in str(e).lower() or 'code' in str(e).lower():
                        form.add_error('subject_code', 'Subject code already exists. Please use a different code.')
                    else:
                        form.add_error(None, 'An error occurred. Please try again.')
                else:
                    form.add_error(None, 'An error occurred. Please try again.')
            except Exception as e:
                form.add_error(None, f'Error creating account: {str(e)}')
    else:
        form = SignUpForm()
    
    return render(request, 'layout/signup.html', {'form': form})

def logout_view(request):
    if request.GET.get('cancel'):
        return redirect('teacher_dashboard')
    username = request.user.get_full_name() or request.user.username
    logout(request)
    messages.info(request, f'👋 See you later, {username}! You have been logged out.')
    return redirect('login')

@login_required
def take_attendance(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get teacher's classes with subject information
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    # Get selected class and students if any
    selected_class = request.POST.get('class') or request.GET.get('class')
    students = []

    if selected_class:
        try:
            class_obj = teacher_classes.get(id=selected_class)
            # Get students directly from the class
            students = Student.objects.filter(class_instance=class_obj)

            if request.method == 'POST':
                # Get date and time from form
                attendance_date = request.POST.get('attendance_date')
                attendance_time = request.POST.get('attendance_time')
                
                if not attendance_date or not attendance_time:
                    messages.error(request, 'Date and time are required.')
                    return redirect('take_attendance')
                
                try:
                    # Convert string time to time object
                    time_obj = timezone.datetime.strptime(attendance_time, '%H:%M:%S').time()
                except ValueError:
                    messages.error(request, 'Invalid time format.')
                    return redirect('take_attendance')
                
                # Process attendance for each student
                for student in students:
                    status = request.POST.get(f'status_{student.id}')
                    if status:
                        # Create or update attendance record
                        Attendance.objects.update_or_create(
                            student=student,  # The actual student
                            class_instance=class_obj,
                            date=attendance_date,
                            defaults={
                                'status': status,
                                'time_in': time_obj
                            }
                        )
                
                messages.success(request, 'Attendance recorded successfully!')
                return redirect('take_attendance')

        except Class.DoesNotExist:
            messages.error(request, 'Invalid class selected.')
            students = []
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            students = []

    return render(request, 'teachers/take_attendance.html', {
        'classes': teacher_classes,
        'selected_class': selected_class,
        'students': students,
        'page_title': 'Take Attendance'
    })

@login_required
def teacher_dashboard(request):
    """View for teacher's dashboard."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    # Get today's date
    today = timezone.now().date()
    
    # Calculate total students (unique students across all classes)
    total_students = ClassEnrollment.objects.filter(
        class_instance__in=teacher_classes
    ).values('student').distinct().count()
    
    # Calculate total classes
    total_classes = teacher_classes.count()
    
    # Get today's attendance records
    today_attendance = Attendance.objects.filter(
        class_instance__in=teacher_classes,
        date=today
    )
    
    # Count present students
    present_today = today_attendance.filter(
        status='present'
    ).values('student').distinct().count()
    
    # Count late students
    late_today = today_attendance.filter(
        status='late'
    ).values('student').distinct().count()
    
    # Count absent students
    absent_today = today_attendance.filter(
        status='absent'
    ).values('student').distinct().count()
    
    # Get class statistics
    class_stats = []
    for class_obj in teacher_classes:
        total_enrolled = ClassEnrollment.objects.filter(class_instance=class_obj).count()
        class_stats.append({
            'class': class_obj,
            'total_enrolled': total_enrolled
        })

    context = {
        'total_students': total_students,
        'total_classes': total_classes,
        'present_today': present_today,
        'late_today': late_today,
        'absent_today': absent_today,
        'class_stats': class_stats,
        'page_title': 'Teacher Dashboard'
    }
    
    return render(request, 'teachers/dashboard.html', context)

@login_required
def get_attendance_stats(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Get teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile)
    
    # Get today's date
    today = timezone.now().date()
    
    # Get today's attendance records
    today_attendance = Attendance.objects.filter(
        class_instance__in=teacher_classes,
        date=today
    )
    
    # Count present students
    present_today = today_attendance.filter(
        status='present'
    ).values('student').distinct().count()
    
    # Count late students
    late_today = today_attendance.filter(
        status='late'
    ).values('student').distinct().count()
    
    # Count absent students
    absent_today = today_attendance.filter(
        status='absent'
    ).values('student').distinct().count()
    
    return JsonResponse({
        'present_today': present_today,
        'late_today': late_today,
        'absent_today': absent_today
    })

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
        'student',
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
        room = request.POST.get('room', 'Default Room')
        
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
                    room=room
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
    
    return redirect('teacher_dashboard')

@login_required
def student_list(request):
    """View for listing students."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get teacher's classes
    teacher_classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    # Get the selected class filter and search query
    selected_class = request.GET.get('class')
    search_query = request.GET.get('search')
    
    # Base query for students - combine both direct assignments and enrollments
    students_list = Student.objects.filter(
        Q(class_instance__teacher=request.user.userprofile) |  # Direct assignments
        Q(enrollments__class_instance__teacher=request.user.userprofile)  # Enrollments
    ).select_related('class_instance', 'class_instance__subject').distinct()

    # Apply filters
    if selected_class:
        try:
            # Verify the class belongs to the teacher
            class_obj = teacher_classes.get(id=selected_class)
            students_list = students_list.filter(
                Q(class_instance=class_obj) |  # Direct assignments
                Q(enrollments__class_instance=class_obj)  # Enrollments
            ).distinct()
        except Class.DoesNotExist:
            messages.error(request, 'Invalid class selected.')
            students_list = Student.objects.none()
    
    # Apply search
    if search_query:
        students_list = students_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(student_id__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(students_list, 10)  # Show 10 students per page
    page_number = request.GET.get('page', 1)
    students = paginator.get_page(page_number)

    context = {
        'students': students,
        'classes': teacher_classes,
        'selected_class': selected_class,
        'total_students': students_list.count(),
        'page_title': 'Student List'
    }
    
    return render(request, 'teachers/student_list.html', context)

@login_required
def add_student(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            gender = request.POST.get('gender')
            contact_number = request.POST.get('contact_number')
            student_id = request.POST.get('id_number')
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

            # Check if student ID already exists
            if Student.objects.filter(student_id=student_id).exists():
                messages.warning(request, f'Student ID "{student_id}" is already in use.')
                return render(request, 'teachers/add_student.html', {
                    'classes': Class.objects.filter(teacher=request.user.userprofile),
                    'form_data': request.POST,
                    'page_title': 'Add Student'
                })

            # Check if email already exists
            if Student.objects.filter(email=email).exists():
                messages.warning(request, f'Email address "{email}" is already registered.')
                return render(request, 'teachers/add_student.html', {
                    'classes': Class.objects.filter(teacher=request.user.userprofile),
                    'form_data': request.POST,
                    'page_title': 'Add Student'
                })

            # Use transaction to ensure both student and enrollment are created
            with transaction.atomic():
                # Create student record
                student = Student.objects.create(
                    student_id=student_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    contact_number=contact_number,
                    gender=gender,
                    class_instance=class_obj  # Direct class assignment
                )

                # Create enrollment record
                ClassEnrollment.objects.create(
                    student=student,
                    class_instance=class_obj
                )

            messages.success(request, f'Student "{first_name} {last_name}" has been added successfully!')
            # Clear form data after successful addition
            return render(request, 'teachers/add_student.html', {
                'classes': Class.objects.filter(teacher=request.user.userprofile),
                'page_title': 'Add Student'
            })

        except IntegrityError as e:
            error_message = str(e).lower()
            if 'unique constraint' in error_message:
                if 'student_id' in error_message:
                    messages.warning(request, 'This Student ID is already registered in the system.')
                elif 'email' in error_message:
                    messages.warning(request, 'This email address is already registered in the system.')
                else:
                    messages.warning(request, 'This student information already exists in the system.')
            else:
                messages.error(request, f'Error adding student: {str(e)}')
            
            return render(request, 'teachers/add_student.html', {
                'classes': Class.objects.filter(teacher=request.user.userprofile),
                'form_data': request.POST,
                'page_title': 'Add Student'
            })

        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
            return render(request, 'teachers/add_student.html', {
                'classes': Class.objects.filter(teacher=request.user.userprofile),
                'form_data': request.POST,
                'page_title': 'Add Student'
            })

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
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            gender = request.POST.get('gender')
            contact_number = request.POST.get('contact_number')
            id_number = request.POST.get('id_number')
            class_id = request.POST.get('class')

            # Verify the class belongs to the teacher
            class_obj = get_object_or_404(Class, id=class_id, teacher=request.user.userprofile)

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

            # Check if ID number exists (excluding current student)
            id_number_exists = UserProfile.objects.filter(
                id_number=id_number
            ).exclude(id=student.id).exists()

            if id_number_exists:
                messages.error(request, 'A student with this ID number already exists.')
                return render(request, 'teachers/edit_student.html', {
                    'student': student,
                    'classes': teacher_classes,
                    'current_class': student.enrolled_classes.filter(class_instance__teacher=request.user.userprofile).first(),
                    'page_title': 'Edit Student'
                })

            # Update user info
            student.user.first_name = first_name
            student.user.last_name = last_name
            student.user.email = email
            student.user.save()

            # Update profile info
            student.gender = gender
            student.contact_number = contact_number
            student.id_number = id_number
            student.save()

            # Update class enrollment
            enrollment = ClassEnrollment.objects.filter(student=student, class_instance__teacher=request.user.userprofile).first()
            if enrollment:
                enrollment.class_instance = class_obj
                enrollment.save()
            else:
                ClassEnrollment.objects.create(student=student, class_instance=class_obj)

            messages.success(request, 'Student updated successfully!')
            return redirect('teacher_dashboard')

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
        student_name = student.user.get_full_name()
        # Delete user (this will cascade delete the profile and enrollments)
        student.user.delete()
        messages.success(request, f'Student "{student_name}" has been deleted')
    except Exception as e:
        messages.error(request, f'Error deleting student: {str(e)}')
    
    # Redirect back to student list with any existing filters
    return redirect(request.META.get('HTTP_REFERER', 'student_list'))

@login_required
def teacher_class_detail(request, class_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get class only if it belongs to the teacher
    class_obj = get_object_or_404(Class, id=class_id, teacher=request.user.userprofile)
    
    # Get all enrolled students
    all_students = Student.objects.filter(class_instance=class_obj).select_related('class_instance')
    
    # Pagination
    paginator = Paginator(all_students, 10)  # Show 10 students per page
    page_number = request.GET.get('page', 1)
    enrolled_students = paginator.get_page(page_number)

    context = {
        'class': class_obj,
        'enrolled_students': enrolled_students,
        'total_students': all_students.count(),
        'page_title': f'Class Detail - {class_obj}'
    }

    return render(request, 'teachers/class_detail.html', context)

@login_required
def get_students(request, class_id):
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
            'email': enrollment.student.user.email,
            'id_number': enrollment.student.id_number or 'N/A'
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
            attendance.save()
            messages.success(request, 'Attendance record updated successfully!')
            return redirect('manage_attendance')
        except Exception as e:
            messages.error(request, f'Error updating attendance: {str(e)}')

    context = {
        'attendance': attendance,
        'page_title': 'Edit Attendance'
    }
    return render(request, 'teachers/edit_attendance.html', context)

@login_required
def attendance_report(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    # Get teacher's classes
    classes = Class.objects.filter(teacher=request.user.userprofile).select_related('subject')
    
    # Get filter parameters
    selected_class = request.GET.get('class')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Initialize attendance data
    attendance_data = []
    selected_class_name = None
    
    if selected_class or from_date or to_date:
        # Base query for attendance records
        attendance_query = Attendance.objects.select_related(
            'student__user', 
            'class_instance__subject'
        )
        
        # Apply class filter
        if selected_class:
            attendance_query = attendance_query.filter(class_instance_id=selected_class)
            try:
                class_obj = Class.objects.get(id=selected_class)
                selected_class_name = f"{class_obj.subject.name} - {class_obj.section}"
            except Class.DoesNotExist:
                messages.error(request, 'Selected class not found.')
                return redirect('attendance_report')
        else:
            attendance_query = attendance_query.filter(class_instance__teacher=request.user.userprofile)
        
        # Apply date filters
        if from_date:
            attendance_query = attendance_query.filter(date__gte=from_date)
        if to_date:
            attendance_query = attendance_query.filter(date__lte=to_date)
        
        # Get unique students
        students = attendance_query.values(
            'student__user__first_name',
            'student__user__last_name',
            'student_id',
            'class_instance__subject__name',
            'class_instance__section'
        ).distinct()
        
        # Calculate statistics for each student
        for student in students:
            student_records = attendance_query.filter(student_id=student['student_id'])
            total_days = student_records.count()
            present_days = student_records.filter(status='present').count()
            absent_days = total_days - present_days
            attendance_rate = round((present_days / total_days * 100), 2) if total_days > 0 else 0
            
            attendance_data.append({
                'student_name': f"{student['student__user__first_name']} {student['student__user__last_name']}",
                'class_name': f"{student['class_instance__subject__name']} - {student['class_instance__section']}",
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'attendance_rate': attendance_rate
            })
    
    context = {
        'classes': classes,
        'selected_class': selected_class,
        'from_date': from_date,
        'to_date': to_date,
        'attendance_data': attendance_data,
        'selected_class_name': selected_class_name,
        'current_date': timezone.now().strftime('%Y-%m-%d'),
        'page_title': 'Attendance Report'
    }
    
    return render(request, 'teachers/reports/attendance_report.html', context)

@login_required
def fix_enrollments(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    try:
        # Get all students with class_instance but no enrollment
        students = Student.objects.filter(
            class_instance__isnull=False,
            enrollments__isnull=True
        )

        # Create enrollments for each student
        enrollment_count = 0
        for student in students:
            ClassEnrollment.objects.create(
                student=student,
                class_instance=student.class_instance
            )
            enrollment_count += 1

        if enrollment_count > 0:
            messages.success(request, f'Successfully fixed enrollments for {enrollment_count} students.')
        else:
            messages.info(request, 'No students needed enrollment fixes.')

    except Exception as e:
        messages.error(request, f'Error fixing enrollments: {str(e)}')

    return redirect('student_list')

@login_required
def fix_student_relationships(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    try:
        with transaction.atomic():
            # Get all students with class_instance but no enrollment
            students_missing_enrollment = Student.objects.filter(
                class_instance__isnull=False,
                enrollments__isnull=True
            )

            # Create enrollments for students with class_instance but no enrollment
            for student in students_missing_enrollment:
                ClassEnrollment.objects.create(
                    student=student,
                    class_instance=student.class_instance
                )

            # Get all students with enrollments but no class_instance
            students_missing_class = Student.objects.filter(
                class_instance__isnull=True,
                enrollments__isnull=False
            )

            # Set class_instance for students with enrollments but no class_instance
            for student in students_missing_class:
                # Get the first enrollment's class
                first_enrollment = student.enrollments.first()
                if first_enrollment:
                    student.class_instance = first_enrollment.class_instance
                    student.save()

            total_fixed = students_missing_enrollment.count() + students_missing_class.count()
            if total_fixed > 0:
                messages.success(request, f'Successfully fixed {total_fixed} student relationships.')
            else:
                messages.info(request, 'No student relationships needed fixing.')

    except Exception as e:
        messages.error(request, f'Error fixing student relationships: {str(e)}')

    return redirect('student_list')

@login_required
def save_attendance(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'teacher':
        messages.error(request, 'Access denied. Teacher access only.')
        return redirect('login')

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        try:
            # Verify the class belongs to the teacher
            class_obj = Class.objects.get(id=class_id, teacher=request.user.userprofile)
            
            # Get all students in the class
            students = Student.objects.filter(class_instance=class_obj)
            
            # Get current date
            current_date = timezone.now().date()
            
            # Process attendance for each student
            for student in students:
                status = request.POST.get(f'status_{student.id}')
                if status:
                    # Create or update attendance record
                    Attendance.objects.update_or_create(
                        student=student,
                        class_instance=class_obj,
                        date=current_date,
                        defaults={
                            'status': status,
                            'time_in': timezone.now().time()
                        }
                    )
            
            # Get updated attendance stats
            today_attendance = Attendance.objects.filter(
                class_instance__in=Class.objects.filter(teacher=request.user.userprofile),
                date=current_date
            )
            
            present_count = today_attendance.filter(status='present').values('student').distinct().count()
            late_count = today_attendance.filter(status='late').values('student').distinct().count()
            absent_count = today_attendance.filter(status='absent').values('student').distinct().count()
            
            messages.success(request, f'Attendance saved successfully! Present: {present_count}, Late: {late_count}, Absent: {absent_count}')
            return redirect('take_attendance')
            
        except Class.DoesNotExist:
            messages.error(request, 'Invalid class selected.')
        except Exception as e:
            messages.error(request, f'Error saving attendance: {str(e)}')
    
    return redirect('take_attendance')

