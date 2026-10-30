from flask import Blueprint, render_template, session, redirect, url_for
from db import get_connection

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
def profile():

    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = "SELECT * FROM users WHERE username=%s"
    cursor.execute(sql, (session['username'],))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("profile.html", user=user)