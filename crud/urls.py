from django.urls import path
from . import views

urlpatterns = [
    path('student/add', views.add_student),
]
