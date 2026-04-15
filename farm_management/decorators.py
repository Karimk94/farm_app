# farm_management/decorators.py
from functools import wraps
from flask import abort, jsonify, request
from flask_login import current_user

def role_required(*roles):
    """
    Decorator that restricts access to routes based on user roles.
    Example usage: @role_required('admin', 'super_user')
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                wants_json = request.is_json or 'application/json' in (request.headers.get('Accept') or '')
                if wants_json:
                    return jsonify({'error': 'forbidden', 'message': 'You do not have permission to access this resource.'}), 403
                # If the user does not have the required role, return a 403 Forbidden error.
                abort(403)
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

