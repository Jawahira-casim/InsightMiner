from flask import Blueprint, render_template
from decorators import login_required
from db import get_connection

about_bp = Blueprint('about', __name__)

@about_bp.route('/about')
@login_required
def about():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    settings = {}

    for row in rows:
        settings[row['setting_key']] = row['setting_value']

    return render_template(
        "about.html",
        settings=settings
    )