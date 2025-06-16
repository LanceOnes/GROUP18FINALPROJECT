from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import UserProfile, Subject

class LoginForm(forms.Form):
    username_or_email = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username or email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username_or_email')
        password = cleaned_data.get('password')
        
        if username_or_email and password:
            # Try to authenticate with username first
            user = authenticate(username=username_or_email, password=password)
            
            if user is None:
                # If username auth fails, try email
                try:
                    user = User.objects.get(email=username_or_email)
                    user = authenticate(username=user.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user is None:
                raise forms.ValidationError('Invalid username/email or password.')
            elif not user.is_active:
                raise forms.ValidationError('This account is inactive.')
            
            cleaned_data['user'] = user
        return cleaned_data

class SignUpForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Choose a username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Create a password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Confirm your password'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter your email'
        })
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter your last name'
        })
    )
    contact_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter your contact number'
        })
    )
    subject_code = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter subject code'
        })
    )
    subject_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter subject name'
        })
    )
    section = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter section'
        })
    )
    room = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 rounded-lg',
            'placeholder': 'Enter room number'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if not password or not confirm_password:
            raise forms.ValidationError('Please fill in all fields.')
            
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
        
        # Check if username already exists
        username = cleaned_data.get('username')
        if username:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('Username already exists.')
        else:
            raise forms.ValidationError('Username is required.')

        # Check if email already exists
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')

        # Validate subject code
        subject_code = cleaned_data.get('subject_code')
        if subject_code:
            # Remove any whitespace
            subject_code = subject_code.strip()
            # Check if subject code already exists
            if Subject.objects.filter(code=subject_code).exists():
                raise forms.ValidationError('Subject code already exists. Please use a different code.')
            # Basic validation for subject code format
            if not subject_code.isalnum():  # Check if alphanumeric
                raise forms.ValidationError('Subject code must contain only letters and numbers.')
            if len(subject_code) < 4:  # Minimum length
                raise forms.ValidationError('Subject code must be at least 4 characters long.')
            cleaned_data['subject_code'] = subject_code
        else:
            raise forms.ValidationError('Subject code is required.')
        
        return cleaned_data 