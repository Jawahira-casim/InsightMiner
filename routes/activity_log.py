from flask import Blueprint, render_template, session, redirect, url_for, request
from db import get_connection
import pandas as pd
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from decorators import role_required

activity_log_bp = Blueprint('activity_log', __name__)

@activity_log_bp.route('/activity')
@role_required('Admin')
def activity():

    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    search = request.args.get('search', '')
    date = request.args.get('date', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT username, activity, activity_time
        FROM activity_logs
        WHERE 1=1
    """

    params = []

    if search:
        sql += " AND (username LIKE %s OR activity LIKE %s)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    if date:
        sql += " AND DATE(activity_time) = %s"
        params.append(date)

    sql += " ORDER BY activity_time DESC"

    cursor.execute(sql, params)
    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "activity.html",
        logs=logs,
        search=search,
        date=date
    )
def get_filtered_logs(search='', date=''):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT username, activity, activity_time
        FROM activity_logs
        WHERE 1=1
    """

    params = []

    if search:
        sql += " AND (username LIKE %s OR activity LIKE %s)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    if date:
        sql += " AND DATE(activity_time) = %s"
        params.append(date)

    sql += " ORDER BY activity_time DESC"

    cursor.execute(sql, params)
    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return logs


@activity_log_bp.route('/activity_excel')
def activity_excel():

    search = request.args.get('search', '')
    date = request.args.get('date', '')

    logs = get_filtered_logs(search, date)

    df = pd.DataFrame(logs)
    df.to_excel("Activity_Log.xlsx", index=False)

    return send_file("Activity_Log.xlsx", as_attachment=True)


@activity_log_bp.route('/activity_pdf')
def activity_pdf():

    search = request.args.get('search', '')
    date = request.args.get('date', '')

    logs = get_filtered_logs(search, date)

    pdf = SimpleDocTemplate("Activity_Log.pdf")
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("IFPS Institute - Activity Log", styles['Title']))
    content.append(Spacer(1, 12))

    data = [["Username", "Activity", "Date & Time"]]

    for log in logs:
        data.append([
            str(log["username"]),
            str(log["activity"]),
            str(log["activity_time"])
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    content.append(table)
    pdf.build(content)

    return send_file("Activity_Log.pdf", as_attachment=True)