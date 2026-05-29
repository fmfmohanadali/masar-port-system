from rest_framework import permissions


def _get_role(user):
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'role', '') if profile else ''


class IsOpsOrAdmin(permissions.BasePermission):
    message = 'هذا الإجراء متاح فقط لمسؤولي العمليات والإدارة'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_role(request.user)
        return role in ['ops', 'port_admin'] or request.user.is_staff


class CanScan(permissions.BasePermission):
    message = 'هذا الإجراء متاح فقط لحراس البوابة والعمليات والإدارة'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_role(request.user)
        return role in ['gate_guard', 'ops', 'port_admin'] or request.user.is_staff


class IsBroker(permissions.BasePermission):
    message = 'هذا الإجراء متاح فقط للمخلصين الجمركيين'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_role(request.user)
        return role == 'broker' or request.user.is_staff


class IsCarrier(permissions.BasePermission):
    message = 'هذا الإجراء متاح فقط لشركات النقل'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_role(request.user)
        return role == 'carrier' or request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    message = 'ليس لديك صلاحية الوصول لهذا العنصر'

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        role = _get_role(request.user)
        if role in ['ops', 'port_admin']:
            return True
        if hasattr(obj, 'broker'):
            return obj.broker == request.user
        if hasattr(obj, 'requester'):
            return obj.requester == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
