from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator

name_validator = RegexValidator(
    regex=r'^[A-Z][a-z]+$',
    message='Must start with uppercase letter, then lowercase letters only.'
)
phone_validator = RegexValidator(
    regex=r'^\+?\d{8,15}$',
    message='Phone number must be 8–15 digits, optional leading +.'
)
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, blank=False, null=False)

    first_name = models.CharField(
        max_length=30,
        blank=True,
        validators=[MinLengthValidator(2), name_validator]
    )

    last_name = models.CharField(
        max_length=30,
        blank=True,
        validators=[MinLengthValidator(2), name_validator]
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator]
    )

    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Automatically capitalize first and last names if set
        if self.first_name:
            self.first_name = self.first_name.capitalize()
        if self.last_name:
            self.last_name = self.last_name.capitalize()
        super().save(*args, **kwargs)