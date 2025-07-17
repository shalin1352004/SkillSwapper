from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Profile, SkillRequest, ChatMessage
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout, authenticate
from django import forms
from django.urls import reverse
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.http import Http404
from django.conf import settings


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    edit_field = None
    error_message = None

    # If profile does not exist (deleted), remove all SkillRequests and ChatMessages involving this user
    if not profile or not Profile.objects.filter(user=request.user).exists():
        SkillRequest.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).delete()
        ChatMessage.objects.filter(sender=request.user).delete()
        # Optionally, you can also log out the user or redirect
        return redirect('logout')

    if request.method == 'POST':
        edit_field = request.POST.get('edit_field')
        if edit_field == 'name':
            name = request.POST.get('name', '').strip()
            if not name:
                error_message = 'Name is required.'
            else:
                profile.name = name
                profile.save()
                return redirect('profile')
        elif edit_field == 'experience':
            experience = request.POST.get('experience', '').strip()
            if not experience:
                error_message = 'Experience is required.'
            else:
                profile.experience = experience
                profile.save()
                return redirect('profile')
        elif edit_field == 'skills':
            new_skills = request.POST.get('skills', '').strip()
            if not new_skills:
                error_message = 'Skills are required.'
            else:
                new_skills_list = [s.strip() for s in new_skills.split(',') if s.strip()]
                profile.skills = ', '.join(new_skills_list)
                profile.save()
                return redirect('profile')
        elif edit_field == 'bio':
            bio = request.POST.get('bio', '').strip()
            if not bio:
                error_message = 'Bio is required.'
            else:
                profile.bio = bio
                profile.save()
                return redirect('profile')
        elif edit_field == 'availability':
            profile.availability = not profile.availability
            profile.save()
            return redirect('profile')
        elif edit_field == 'avatar':
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
                profile.save()
            return redirect('profile')

    # Optionally, support GET param to show which field to edit
    if request.method == 'GET':
        edit_field = request.GET.get('edit', None)

    return render(request, 'profile.html', {'profile': profile, 'edit_field': edit_field, 'error_message': error_message})


@login_required
def home_view(request):
    query = request.GET.get('q', '').strip()
    # Exclude users who are already connected (accepted) with current user
    # Also exclude users who have pending requests with current user (in either direction)
    connected_ids = SkillRequest.objects.filter(
        (
            models.Q(sender=request.user) | models.Q(receiver=request.user)
        ),
        status='Accepted'
    ).values_list('sender_id', 'receiver_id')
    
    # Get users with pending requests (in either direction)
    pending_ids = SkillRequest.objects.filter(
        (
            models.Q(sender=request.user) | models.Q(receiver=request.user)
        ),
        status='Pending'
    ).values_list('sender_id', 'receiver_id')
    
    exclude_ids = {request.user.id}
    for sender_id, receiver_id in connected_ids:
        exclude_ids.add(sender_id)
        exclude_ids.add(receiver_id)
    for sender_id, receiver_id in pending_ids:
        exclude_ids.add(sender_id)
        exclude_ids.add(receiver_id)
    
    # Exclude admin and staff users from being displayed
    profiles = Profile.objects.exclude(
        models.Q(user__id__in=exclude_ids) |
        models.Q(user__is_staff=True) |
        models.Q(user__is_superuser=True)
    ).exclude(
        models.Q(skills='') | 
        models.Q(skills__isnull=True)
    )
    
    if query:
        profiles = profiles.filter(
            models.Q(user__username__icontains=query) |
            models.Q(skills__icontains=query)
        )

    # Annotate each profile with request_status
    for profile in profiles:
        req = SkillRequest.objects.filter(
            (
                (models.Q(sender=request.user, receiver=profile.user) |
                 models.Q(sender=profile.user, receiver=request.user))
            )
        ).order_by('-created_at').first()
        if req:
            profile.request_status = req.status.lower()  # 'pending', 'accepted', 'rejected'
        else:
            profile.request_status = None

    return render(request, 'home.html', {
        'profiles': profiles, 
        'query': query
    })


def landing_view(request):
    return render(request, 'landing.html')


@login_required
def dashboard_view(request):
    received_requests = SkillRequest.objects.filter(receiver=request.user)
    sent_requests = SkillRequest.objects.filter(sender=request.user)
    return render(request, 'dashboard.html', {
        'received': received_requests,
        'sent': sent_requests,
    })


def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = None
            if user:
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('home')
            form.add_error(None, "Invalid email or password.")
    else:
        form = EmailAuthenticationForm()
    return render(request, 'login.html', {'form': form})
def chat_mobile_view(request):
    messages = ChatMessage.objects.all()  # Or filter based on user/chatroom
    return render(request, 'chat_mobile.html', {'messages': messages})


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data.get('email', '')
            user.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('profile')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


@login_required
@csrf_exempt
def send_request_view(request, user_id):
    if request.method == 'POST':
        if user_id == request.user.id:
            return redirect('home')
        receiver = get_object_or_404(User, id=user_id)
        
        # Prevent sending requests to admin or staff users
        if receiver.is_staff or receiver.is_superuser:
            return redirect('home')
        
        # Prevent sending a request if there is already a pending request between these users (in either direction)
        existing = SkillRequest.objects.filter(
            (
                (models.Q(sender=request.user, receiver=receiver) |
                 models.Q(sender=receiver, receiver=request.user))
            ),
            status='Pending'
        ).exists()
        if not existing:
            skill = request.POST.get('skill_needed')
            SkillRequest.objects.create(sender=request.user, receiver=receiver, skill_needed=skill)
        return redirect('home')
    return redirect('home')


@login_required
def respond_request_view(request, req_id):
    req = get_object_or_404(SkillRequest, id=req_id, receiver=request.user)
    action = request.GET.get('action')
    
    if action == 'accept':
        req.status = 'Accepted'
        message = 'Request accepted successfully!'
    elif action == 'reject':
        req.status = 'Rejected'
        message = 'Request rejected.'
    else:
        return JsonResponse({'success': False, 'message': 'Invalid action'})
    
    req.save()
    return JsonResponse({'success': True, 'message': message, 'status': req.status})


@login_required
def chat_view(request, req_id):
    req = get_object_or_404(SkillRequest, id=req_id)
    if req.status != 'Accepted' or (request.user != req.sender and request.user != req.receiver):
        return redirect('dashboard')
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            ChatMessage.objects.create(request=req, sender=request.user, message=message)
    messages = ChatMessage.objects.filter(request=req).order_by('timestamp')

    # Mark all unread messages sent to the current user as read
    ChatMessage.objects.filter(request=req, read=False).filter(~Q(sender=request.user)).update(read=True)

    return render(request, 'chat.html', {'request_obj': req, 'messages': messages})


@login_required
def chat_ajax_view(request, req_id):
    req = get_object_or_404(SkillRequest, id=req_id)
    if req.status != 'Accepted' or (request.user != req.sender and request.user != req.receiver):
        return redirect('dashboard')
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            ChatMessage.objects.create(request=req, sender=request.user, message=message)
    messages = ChatMessage.objects.filter(request=req).order_by('timestamp')

    # Mark all unread messages sent to the current user as read
    ChatMessage.objects.filter(request=req, read=False).filter(~Q(sender=request.user)).update(read=True)

    return render(request, 'chat_ajax.html', {'request_obj': req, 'messages': messages})


def user_profile_view(request, user_id):
    # Don't allow viewing your own profile via this route
    if request.user.id == user_id:
        return redirect('profile')
    # Don't allow viewing admin/staff profiles
    user = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)
    profile = get_object_or_404(Profile, user=user)
    # Only show users with skills
    if not profile.skills:
        raise Http404()
    return render(request, 'user_profile.html', {'profile': profile})


def logout_view(request):
    logout(request)
    return render(request, 'logout.html')


@login_required
def requests_sent_view(request):
    sent_requests = SkillRequest.objects.filter(sender=request.user)
    return render(request, 'requests_sent.html', {'sent': sent_requests})


@login_required
def requests_received_view(request):
    received_requests = SkillRequest.objects.filter(receiver=request.user)
    # Mark all pending and accepted requests as seen
    SkillRequest.objects.filter(
        receiver=request.user,
        status__in=['Pending', 'Accepted'],
        seen_by_receiver=False
    ).update(seen_by_receiver=True)
    return render(request, 'requests_received.html', {'received': received_requests})


def test_bg_view(request):
    return render(request, 'test_bg.html')

@login_required
def chat_list_view(request):
    # Get all accepted requests involving the user, newest first
    requests = SkillRequest.objects.filter(
        models.Q(sender=request.user) | models.Q(receiver=request.user),
        status='Accepted'
    ).order_by('-created_at')
    chat_map = {}
    for req in requests:
        other = req.receiver if req.sender == request.user else req.sender
        if other.id not in chat_map:
            req.other_user = other
            chat_map[other.id] = req
    chats = list(chat_map.values())
    
    # Mark all unread messages sent to the current user as read
    ChatMessage.objects.filter(request__in=requests, read=False).exclude(sender=request.user).update(read=True)
    
    # Check if a specific chat is selected
    selected_chat_id = request.GET.get('chat_id')
    selected_chat = None
    selected_chat_messages = []
    
    if selected_chat_id:
        try:
            selected_chat = next((chat for chat in chats if chat.id == int(selected_chat_id)), None)
            if selected_chat:
                selected_chat_messages = ChatMessage.objects.filter(request=selected_chat).order_by('timestamp')
        except (ValueError, TypeError):
            pass
    
    return render(request, 'chat_list.html', {
        'chats': chats,
        'selected_chat': selected_chat,
        'selected_chat_messages': selected_chat_messages
    })


def notification_context(request):
    if not request.user.is_authenticated:
        return {}

    # Unread chat messages (messages sent to user, not read)
    unread_count = ChatMessage.objects.filter(
        request__status='Accepted',
        read=False
    ).exclude(sender=request.user).filter(
        models.Q(request__sender=request.user) | models.Q(request__receiver=request.user)
    ).count()

    # Requests (pending or accepted) not yet seen by user (as receiver)
    unseen_requests = SkillRequest.objects.filter(
        receiver=request.user,
        status__in=['Pending', 'Accepted'],
        seen_by_receiver=False
    ).count()

    return {
        'unread_chat_count': unread_count,
        'unseen_accepted_request_count': unseen_requests,
    }
