from django.conf import settings
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models
from django.db.models import Max
from django.utils import timezone


class CustomUserManager(BaseUserManager):

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username


class Board(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                     related_name='boards')

    def __str__(self):
        return self.name


class List(models.Model):
    name = models.CharField(max_length=255)
    board = models.ForeignKey('Board',
                              on_delete=models.CASCADE,
                              related_name='lists')
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position']

    def save(self, *args, **kwargs):
        if not self.position:
            max_position = List.objects.filter(board=self.board).aggregate(
                Max('position'))['position__max']
            self.position = max_position + 1 if max_position is not None else 0
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Task(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(choices=[(1, 'Low'), (2, 'Medium'),
                                            (3, 'High')],
                                   default=1)
    complexity = models.IntegerField(choices=[(1, 'Easy'), (2, 'Medium'),
                                              (3, 'Hard')],
                                     default=1)
    list = models.ForeignKey('List',
                             on_delete=models.CASCADE,
                             related_name='tasks')
    assigned_to = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                         related_name='assigned_tasks')
    position = models.IntegerField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return self.title

    def complete(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def is_overdue(self):
        return self.due_date and self.due_date < timezone.now(
        ) and not self.completed

    def save(self, *args, **kwargs):
        if self.position is None:
            max_position = Task.objects.filter(list=self.list).aggregate(
                Max('position'))['position__max']
            self.position = max_position + 1 if max_position is not None else 0
        super().save(*args, **kwargs)


class JournalEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name='journal_entries')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    task = models.ForeignKey('Task',
                             on_delete=models.SET_NULL,
                             null=True,
                             blank=True,
                             related_name='journal_entries')
    valence = models.FloatField(null=True, blank=True)
    arousal = models.FloatField(null=True, blank=True)
    visibility = models.CharField(max_length=10,
                                  choices=[('private', 'Private'),
                                           ('shared', 'Shared'),
                                           ('public', 'Public')],
                                  default='private')
    shared_with = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                         related_name='shared_journal_entries',
                                         blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
