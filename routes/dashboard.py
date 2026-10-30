from flask import Blueprint, render_template, session, redirect, url_for
from db import get_connection

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def dashboard():

    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    users = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM datasets")
    datasets = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM activity_logs")
    activities = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM datasets
        WHERE DATE(upload_date) = CURDATE()
    """)
    uploaded_today = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE is_read = 0
    """)
    notifications = cursor.fetchone()['total']

    quality_score = 95

    cursor.execute("""
        SELECT username, activity, activity_time
        FROM activity_logs
        ORDER BY activity_time DESC
        LIMIT 5
    """)
    recent_activities = cursor.fetchall()

    cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)
    settings_rows = cursor.fetchall()

    settings = {}
    for row in settings_rows:
        settings[row['setting_key']] = row['setting_value']

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        users=users,
        datasets=datasets,
        activities=activities,
        uploaded_today=uploaded_today,
        notifications=notifications,
        quality_score=quality_score,
        recent_activities=recent_activities,
        settings=settings
    )