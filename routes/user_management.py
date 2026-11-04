
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file
)

from db import get_connection
from decorators import role_required
from activity import log_activity
from notification_helper import add_notification

from werkzeug.security import generate_password_hash

import pandas as pd
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4


user_management_bp = Blueprint('user_management', __name__)


# USER MANAGEMENT PAGE
@user_management_bp.route('/users')
@role_required('Admin')
def users():

    search = request.args.get('search', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if search:
            cursor.execute(
                """
                SELECT id, username, role
                FROM users
                WHERE username LIKE %s OR role LIKE %s
                """,
                (f"%{search}%", f"%{search}%")
            )
        else:
            cursor.execute(
                "SELECT id, username, role FROM users"
            )

        users = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "users.html",
        users=users,
        search=search
    )


# ADD NEW USER
@user_management_bp.route('/add_user', methods=['POST'])
@role_required('Admin')
def add_user():

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
            """,
            (username, hashed_password, role)
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    if session.get('username'):
        log_activity(
            session['username'],
            f"Created new user: {username}"
        )

        add_notification(
            session['username'],
            f"New user '{username}' created successfully."
        )

    flash("User created successfully.", "success")

    return redirect(url_for('user_management.users'))


# CHANGE USER ROLE
@user_management_bp.route('/change_role/<int:user_id>', methods=['POST'])
@role_required('Admin')
def change_role(user_id):

    new_role = request.form['role']

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE users SET role=%s WHERE id=%s",
            (new_role, user_id)
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    if session.get('username'):
        add_notification(
            session['username'],
            f"Changed user ID {user_id} role to {new_role}."
        )

        log_activity(
            session['username'],
            f"Changed user ID {user_id} role to {new_role}"
        )

        flash("Role updated successfully.", "success")

    return redirect(url_for('user_management.users'))


# DELETE USER
@user_management_bp.route('/delete_user/<int:user_id>')
@role_required('Admin')
def delete_user(user_id):

    if user_id == 1:
        return "Admin user cannot be deleted."

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM users WHERE id=%s",
            (user_id,)
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    if session.get('username'):
        add_notification(
            session['username'],
            f"User ID {user_id} deleted successfully."
        )

        log_activity(
            session['username'],
            f"Deleted user ID {user_id}"
        )

        flash("User deleted successfully.", "success")

    return redirect(url_for('user_management.users'))


# GET ALL USERS
def get_users():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, username, role
            FROM users
            ORDER BY id
        """)

        users = cursor.fetchall()

        return users

    finally:
        cursor.close()
        conn.close()


# EXPORT USERS TO EXCEL
@user_management_bp.route('/users_excel')
@role_required('Admin')
def users_excel():

    users = get_users()

    df = pd.DataFrame(
        users,
        columns=['id', 'username', 'role']
    )

    df.rename(columns={
        'id': 'ID',
        'username': 'Username',
        'role': 'Role'
    }, inplace=True)

    # Generate Excel file in memory
    excel_buffer = BytesIO()

    df.to_excel(
        excel_buffer,
        index=False,
        engine='openpyxl'
    )

    excel_buffer.seek(0)

    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='Users_Report.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# EXPORT USERS TO PDF
@user_management_bp.route('/users_pdf')
@role_required('Admin')
def users_pdf():

    users = get_users()

    # Generate PDF file in memory
    pdf_buffer = BytesIO()

    pdf = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4)
    )

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "InsightMiner - User Management Report",
            styles['Title']
        )
    )

    content.append(Spacer(1, 12))

    data = [["ID", "Username", "Role"]]

    for user in users:
        data.append([
            str(user["id"]),
            str(user["username"] or ""),
            str(user["role"] or "")
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    content.append(table)

    pdf.build(content)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name='Users_Report.pdf',
        mimetype='application/pdf'
    )
