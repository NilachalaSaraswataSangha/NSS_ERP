from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# Model 1 - Role

class Role(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "role"

        ordering = ["name"]

    def __str__(self):

        return self.name
    
# Model 2 - UserRole
class UserRole(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_roles"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="role_users"
    )

    is_primary = models.BooleanField(
        default=False
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = "user_role"

        unique_together = (
            "user",
            "role"
        )

    def __str__(self):

        return (
            f"{self.user.username} - {self.role.name}"
        )


# Model 3 - LoginAudit
class LoginAudit(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    login_time = models.DateTimeField(
        auto_now_add=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField(
        blank=True,
        null=True
    )

    success = models.BooleanField(
        default=True
    )

    class Meta:

        db_table = "login_audit"

        ordering = ["-login_time"]

    def __str__(self):

        username = (
            self.user.username
            if self.user
            else "Unknown"
        )

        return (
            f"{username} - {self.login_time}"
        )