from django.urls import path
from . import views


urlpatterns = [
    # Authentication urls
    path('', views.login_view, name='login'),  
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    
    
    # Teacher urls
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/attendance/', views.manage_attendance, name='manage_attendance'),
    path('teacher/attendance/take/', views.take_attendance, name='take_attendance'),
    path('teacher/reports/attendance/', views.attendance_report, name='attendance_report'),
    path('get-students/<int:class_id>/', views.get_students, name='get_students'),
    path('teacher/class/add/', views.add_class, name='add_class'),
    path('teacher/class/<int:class_id>/', views.teacher_class_detail, name='teacher_class_detail'),
    path('teacher/class/<int:class_id>/edit/', views.edit_class, name='edit_class'),
    path('teacher/class/<int:class_id>/delete/', views.delete_class, name='delete_class'),
    path('teacher/studentlist/', views.student_list, name='student_list'),
    path('teacher/fix-enrollments/', views.fix_enrollments, name='fix_enrollments'),
    path('teacher/attendance/save/', views.save_attendance, name='save_attendance'),
    
    # Student urls
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    
    # Attendance urls
    path('attendance/<int:record_id>/edit/', views.edit_attendance, name='edit_attendance'),
    path('attendance/<int:record_id>/delete/', views.delete_attendance, name='delete_attendance'),
    path('attendance/', views.manage_attendance, name='attendance'),
    path('get-attendance-stats/', views.get_attendance_stats, name='get_attendance_stats'),
    path('fix-student-relationships/', views.fix_student_relationships, name='fix_student_relationships'),
]
