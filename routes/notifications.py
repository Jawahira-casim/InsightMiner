from flask import Blueprint, render_template, redirect, url_for, session
from db import get_connection
from decorators import login_required

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
@login_required
def notifications():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM notifications
        ORDER BY created_at DESC
    """)

    notifications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )
@notifications_bp.route('/notification/read/<int:id>')
@login_required
def mark_as_read(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read = TRUE
        WHERE id=%s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('notifications.notifications'))