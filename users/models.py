from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_primary = models.CharField(max_length=20, blank=True, verbose_name="Основний телефон")
    phone_secondary = models.CharField(max_length=20, blank=True, verbose_name="Додатковий телефон")
    city = models.CharField(max_length=100, blank=True, verbose_name="Місто / Село")
    nova_poshta_branch = models.CharField(max_length=120, blank=True, verbose_name="Відділення або поштомат НП")

    def __str__(self):
        return f"Профіль {self.user.username}"
