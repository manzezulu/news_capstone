"""Role-based DRF permissions built on Django group permissions."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import CustomUser


class RolePermission(BasePermission):
    """Map HTTP method -> Django model permission (view/add/change/delete).

    The view declares ``model_name`` ('article' or 'newsletter').
    """

    method_actions = {
        'GET': 'view',
        'HEAD': 'view',
        'OPTIONS': 'view',
        'POST': 'add',
        'PUT': 'change',
        'PATCH': 'change',
        'DELETE': 'delete',
    }

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        action = self.method_actions.get(request.method)
        return action is not None and user.has_perm(
            f'news.{action}_{view.model_name}'
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        # Editors can modify anything; journalists only their own work
        return user.role == CustomUser.Role.EDITOR or obj.author_id == user.id


class IsReader(BasePermission):
    """Only users with the Reader role."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == CustomUser.Role.READER
        )
