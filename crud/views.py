from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib import messages
from .models import Genders, Students
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import logout
from django.urls import reverse
from django.core.paginator import Paginator
from django.http import JsonResponse
# Create your views here.

def add_student(request): 
    try:
        if request.method == 'POST':
            name = request.POST.get('name')
            age = request.POST.get('age')
            gender_id = request.POST.get('gender_id')
            address = request.POST.get('address')
            
            # Create and save student with all fields
            Students.objects.create(
                name=name,
                age=age,
                gender_id=gender_id,
                address=address
            )
            
            messages.success(request, 'Student added successfully!')
            return redirect('/student/list')
        else:
            genders = Genders.objects.all()  # Get genders for dropdown
            return render(request, 'student/AddStudent.html', {'genders': genders})
    except Exception as e:
        messages.error(request, f'Error adding student: {e}')
        return redirect('/student/add')
