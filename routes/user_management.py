from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection
from decorators import role_required
from activity import log_activity
import pandas as pd
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from notification_helper import add_notification
from werkzeug.security import generate_password_hash

user_management_bp = Blueprint('user_management', __name__)

@user_management_bp.route('/users')
@role_required('Admin')
def users():

    search = request.args.get('search', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute(
            "SELECT id, username, role FROM users WHERE username LIKE %s OR role LIKE %s",
            (f"%{search}%", f"%{search}%")
        )
    else:
        cursor.execute("SELECT id, username, role FROM users")

    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("users.html", users=users, search=search)

@user_management_bp.route('/add_user', methods=['POST'])
@role_required('Admin')
def add_user():

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
        (username, hashed_password, role)
    )

    conn.commit()

    if session.get('username'):
        log_activity(session['username'], f"Created new user: {username}")
        add_notification(session['username'], f"New user '{username}' created successfully.")

    cursor.close()
    conn.close()

    flash("User created successfully.", "success")

    return redirect(url_for('user_management.users'))

@user_management_bp.route('/change_role/<int:user_id>', methods=['POST'])
@role_required('Admin')
def change_role(user_id):

    new_role = request.form['role']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id))
    conn.commit()
    if session.get('username'):
     add_notification(
        session['username'],
        f"Changed user ID {user_id} role to {new_role}."
    )

    cursor.close()
    conn.close()

    if session.get('username'):
        log_activity(session['username'], f"Changed user ID {user_id} role to {new_role}")
        flash("Role updated successfully.", "success")

    return redirect(url_for('user_management.users'))


@user_management_bp.route('/delete_user/<int:user_id>')
@role_required('Admin')
def delete_user(user_id):

    if user_id == 1:
        return "Admin user cannot be deleted."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    if session.get('username'):
     add_notification(
        session['username'],
        f"User ID {user_id} deleted successfully."
    )

    cursor.close()
    conn.close()

    if session.get('username'):
        log_activity(session['username'], f"Deleted user ID {user_id}")
        flash("User deleted successfully.", "success")

    return redirect(url_for('user_management.users'))

def get_users():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, username, role
        FROM users
        ORDER BY id
    """)

    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return users

@user_management_bp.route('/users_excel')
@role_required('Admin')
def users_excel():

    users = get_users()

    df = pd.DataFrame(users)

    filename = "Users_Report.xlsx"

    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)

@user_management_bp.route('/users_pdf')
@role_required('Admin')
def users_pdf():

    users = get_users()

    pdf = SimpleDocTemplate("Users_Report.pdf")
    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph("InsightMiner - User Management Report", styles['Title'])
    )

    content.append(Spacer(1, 12))

    data = [["ID", "Username", "Role"]]

    for user in users:

        data.append([
            str(user["id"]),
            user["username"],
            user["role"]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
    ]))

    content.append(table)

    pdf.build(content)

    return send_file("Users_Report.pdf", as_attachment=True)