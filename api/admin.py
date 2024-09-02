from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Board, CustomUser, JournalEntry, List, Task


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'is_staff', 'is_active']
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')
        }),
    )
    add_fieldsets = ((None, {
        'classes': ('wide', ),
        'fields':
        ('username', 'password1', 'password2', 'is_staff', 'is_active')
    }), )
    search_fields = ('username', )
    ordering = ('username', )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Board)
admin.site.register(List)
admin.site.register(Task)
admin.site.register(JournalEntry)
