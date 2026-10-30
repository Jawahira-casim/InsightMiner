from functools import wraps
from flask import session, redirect, url_for, render_template
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('auth.login'))

            if session.get('role') not in roles:
                return render_template("403.html"), 403

            return func(*args, **kwargs)
        return wrapper
    return decorator