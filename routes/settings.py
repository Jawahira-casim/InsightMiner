from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_connection
from decorators import role_required
from activity import log_activity
from notification_helper import add_notification

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@role_required('Admin')
def settings():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        for key in request.form:

            value = request.form[key]

            cursor.execute(
                """
                UPDATE system_settings
                SET setting_value=%s
                WHERE setting_key=%s
                """,
                (value, key)
            )

        conn.commit()
        if session.get('username'):

         add_notification(
        session['username'],
        "System settings updated."
    )

        log_activity(session['username'], "Updated System Settings")

        flash("System settings updated successfully.", "success")

        return redirect(url_for('settings.settings'))

    cursor.execute("SELECT * FROM system_settings")

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("settings.html", settings=rows)