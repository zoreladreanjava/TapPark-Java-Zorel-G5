from functools import wraps

from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Allow a view only for users whose role is one of `roles`.

    Use it under @login_required, e.g.

        @login_required
        @role_required("ADMIN")
        def admin_dashboard(request): ...

    Any other role gets the 403 "Access denied" page.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
