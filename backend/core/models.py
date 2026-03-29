from django.contrib.auth.models import AbstractUser
from django.db import models


BRANCH_CHOICES = [
    ('engineering', 'Engineering'),
    ('commerce', 'Commerce'),
    ('architecture', 'Architecture'),
]


class User(AbstractUser):
    branch = models.CharField(max_length=50, choices=BRANCH_CHOICES)


class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.CharField(max_length=50, choices=BRANCH_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} [{self.branch}]"


class AccessRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_access_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One pending/approved request per user per document at a time
        unique_together = ('document', 'requester')

    def __str__(self):
        return f"{self.requester.username} → {self.document.title} [{self.status}]"