from rest_framework import permissions


class IsOpsOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(getattr(request.user, 'profile', None), 'role', '')
        return role in ['ops', 'port_admin'] or request.user.is_staff


class CanScan(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(getattr(request.user, 'profile', None), 'role', '')
        return role in ['gate_guard', 'ops', 'port_admin'] or request.user.is_staff
