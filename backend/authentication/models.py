from django.db import models
from django.contrib.auth.models import User


class Role(models.Model):

    role_name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.role_name


class UserRole(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"{self.user.username} - {self.role.role_name}"