from rest_framework import permissions
from .models import UserRole

class IsAdminRole(permissions.BasePermission):
    """
    Allows access only to users with the ADMIN role or superusers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == UserRole.ADMIN or request.user.is_superuser)
        )

class IsOperatorRole(permissions.BasePermission):
    """
    Allows access to users with OPERATOR or ADMIN roles.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role in [UserRole.ADMIN, UserRole.OPERATOR] or request.user.is_superuser)
        )

class IsViewerRole(permissions.BasePermission):
    """
    Allows read-only access to VIEWER users, while write operations require OPERATOR or ADMIN.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.role in [UserRole.ADMIN, UserRole.OPERATOR] or request.user.is_superuser
