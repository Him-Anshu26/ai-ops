from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from accounts.managers import UserManager



# User Model
class User(AbstractUser):
    username = None  # remove username

    email = models.EmailField(unique=True, db_index=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    is_verified = models.BooleanField(default=False)

    auth_provider = models.CharField(
        max_length=20,
        choices=(
            ('local', 'Local'),
            ('google', 'Google'),
        ),
        default='local'
    )

    provider_id = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # normalize email
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email



# Email Verification Token Model
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_tokens"
    )

    token_hash = models.CharField(max_length=255, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def is_expired(self):
        # 24 hours expiry
        return timezone.now() > self.created_at + timezone.timedelta(hours=24)

    def __str__(self):
        return f"EmailToken(user_id={self.user_id})"



# Password Reset Token Model
class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )

    token_hash = models.CharField(max_length=255, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def is_expired(self):
        # 30 minutes expiry
        return timezone.now() > self.created_at + timezone.timedelta(minutes=30)

    def __str__(self):
        return f"PasswordResetToken(user_id={self.user_id})"



# User Session Model
class UserSession(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    session_id = models.CharField(max_length=255, unique=True, db_index=True)

    refresh_token_hash = models.CharField(max_length=255, db_index=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id', 'is_active']),
            models.Index(fields=['user', 'is_active']),
    ]

    def __str__(self):
        # even if user is deleted, we can still show session info otherwise if user.email is used then crash risk
        return f"Session(user_id={self.user_id}, active={self.is_active})"