"""Role-based DRF permissions built on Django group permissions."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import CustomUser


class RolePermission(BasePermission):
    """Authorise API requests by role.

    Maps each HTTP method to the matching Django model permission
    (view, add, change or delete) and allows the request only if the
    user's group holds that permission.
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
        """Check whether the user may use this endpoint at all.

        Anonymous users are always refused. For logged-in users the
        HTTP method is looked up in ``method_actions`` and the matching
        Django model permission (for example ``news.add_article``) is
        required. Methods that are not in ``method_actions`` are denied.

        :param request: The incoming API request
        :type request: rest_framework.request.Request
        :param view: The view handling the request; it must define
            ``model_name`` (for example ``"article"``)
        :type view: rest_framework.views.APIView
        :returns: ``True`` if the user is authenticated and holds the
            permission for this method, ``False`` otherwise
        :rtype: bool
        """
        user = request.user
        if not (user and user.is_authenticated):
            return False
        action = self.method_actions.get(request.method)
        return action is not None and user.has_perm(
            f'news.{action}_{view.model_name}'
        )

    def has_object_permission(self, request, view, obj):
        """Check whether the user may act on one specific object.

        Safe (read-only) methods are always allowed. For anything that
        changes data, editors may modify any object, while other users
        may modify only objects they authored.

        :param request: The incoming API request
        :type request: rest_framework.request.Request
        :param view: The view handling the request
        :type view: rest_framework.views.APIView
        :param obj: The object being accessed; it must have an
            ``author_id`` attribute
        :type obj: django.db.models.Model
        :returns: ``True`` if the request is read-only, the user is an
            editor, or the user is the object's author; ``False``
            otherwise
        :rtype: bool
        """
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        # Editors can modify anything; journalists only their own work
        return user.role == CustomUser.Role.EDITOR or obj.author_id == user.id


class IsReader(BasePermission):
    """Only users with the Reader role."""

    def has_permission(self, request, view):
        """Allow access only to authenticated users with the Reader role.

        :param request: The incoming API request
        :type request: rest_framework.request.Request
        :param view: The view handling the request
        :type view: rest_framework.views.APIView
        :returns: ``True`` if the user is logged in and their role is
            Reader, ``False`` otherwise
        :rtype: bool
        """
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == CustomUser.Role.READER
        )
