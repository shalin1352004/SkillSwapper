# models.py
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)
    experience = models.CharField(max_length=255, blank=True)
    skills = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    availability = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email = models.EmailField(blank=True, null=True)  # Optional email field

    def __str__(self):
        return f"{self.user.username}'s Profile"
        
class SkillRequest(models.Model):
    sender = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    skill_needed = models.CharField(max_length=100)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    seen_by_receiver = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} → {self.receiver} ({self.status})"

class ChatMessage(models.Model):
    request = models.ForeignKey(SkillRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Chat from {self.sender.username} at {self.timestamp}"