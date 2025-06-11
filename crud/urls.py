from django.urls import path
from . import views


urlpatterns = [
    # Authentication URLs
    path('', views.login_view, name='login'),  # Root URL is login
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    
    
    # Teacher URLs
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/attendance/', views.manage_attendance, name='manage_attendance'),
    path('teacher/class/add/', views.add_class, name='add_class'),
    path('teacher/studentlist/', views.student_list, name='student_list'),
    path('teacher/attendance/report/', views.attendance_report, name='attendance_report'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    
    # Attendance URLs
    path('attendance/<int:record_id>/edit/', views.edit_attendance, name='edit_attendance'),
    path('attendance/<int:record_id>/delete/', views.delete_attendance, name='delete_attendance'),
    path('attendance/', views.manage_attendance, name='attendance'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),
]
