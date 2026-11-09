from flask import Blueprint, render_template, request, session, redirect, url_for
from db import get_connection
from activity import log_activity
from flask import session
account_bp = Blueprint('account', __name__)
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app as app


@account_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():

    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    message = None
    status = None

    if request.method == 'POST':

        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not old_password or not new_password or not confirm_password:
            message = "Please fill in all password fields."
            status = "danger"

        elif new_password != confirm_password:
            message = "New password and confirm password do not match."
            status = "danger"

        elif old_password == new_password:
            message = "New password must be different from the current password."
            status = "danger"

        else:
            conn = None
            cursor = None

            try:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT password FROM users WHERE username=%s",
                    (session['username'],)
                )

                user = cursor.fetchone()

                if user and check_password_hash(user[0], old_password):

                    hashed_password = generate_password_hash(new_password)

                    cursor.execute(
                        "UPDATE users SET password=%s WHERE username=%s",
                        (hashed_password, session['username'])
                    )

                    conn.commit()

                    log_activity(
                        session['username'],
                        "Changed Password"
                    )

                    message = "Password changed successfully."
                    status = "success"

                else:
                    message = "Current password is incorrect."
                    status = "danger"

            except Exception:
                if conn and conn.is_connected():
                    conn.rollback()

                app.logger.exception("Password change failed")

                message = "Unable to change password. Please try again."
                status = "danger"

            finally:
                if cursor:
                    cursor.close()

                if conn and conn.is_connected():
                    conn.close()

    return render_template(
        "change_password.html",
        message=message,
        status=status
    )

@account_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    message = None
    status = None

    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            message = "New password and confirm password do not match."
            status = "danger"
            return render_template("forgot_password.html", message=message, status=status)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user:
            cursor.execute(
                "UPDATE users SET password=%s WHERE username=%s",
                   (generate_password_hash(new_password), username)
            )
            conn.commit()
            
            message = "Password reset successfully. You can now login."
            status = "success"
        else:
            message = "Username not found."
            status = "danger"

        cursor.close()
        conn.close()
         
 
    return render_template("forgot_password.html", message=message, status=status)