from rest_framework import permissions


class IsBoardMember(permissions.BasePermission):
    """
    Custom permission to only allow members of a board to access it.
    """

    def has_object_permission(self, request, view, obj):
        return request.user in obj.members.all()
