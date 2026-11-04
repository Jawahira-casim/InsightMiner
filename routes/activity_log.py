
from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    send_file
)

from db import get_connection
from decorators import role_required

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


activity_log_bp = Blueprint('activity_log', __name__)


# ACTIVITY LOG PAGE
@activity_log_bp.route('/activity')
@role_required('Admin')
def activity():

    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    search = request.args.get('search', '')
    date = request.args.get('date', '')

    logs = get_filtered_logs(search, date)

    return render_template(
        "activity.html",
        logs=logs,
        search=search,
        date=date
    )


# GET FILTERED ACTIVITY LOGS
def get_filtered_logs(search='', date=''):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
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

        return logs

    finally:
        cursor.close()
        conn.close()


# EXPORT ACTIVITY LOG TO EXCEL
@activity_log_bp.route('/activity_excel')
@role_required('Admin')
def activity_excel():

    search = request.args.get('search', '')
    date = request.args.get('date', '')

    logs = get_filtered_logs(search, date)

    df = pd.DataFrame(
        logs,
        columns=['username', 'activity', 'activity_time']
    )

    df.rename(columns={
        'username': 'Username',
        'activity': 'Activity',
        'activity_time': 'Date & Time'
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
        download_name='Activity_Log.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# EXPORT ACTIVITY LOG TO PDF
@activity_log_bp.route('/activity_pdf')
@role_required('Admin')
def activity_pdf():

    search = request.args.get('search', '')
    date = request.args.get('date', '')

    logs = get_filtered_logs(search, date)

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
            "IFPS Institute - Activity Log",
            styles['Title']
        )
    )

    content.append(Spacer(1, 12))

    data = [[
        "Username",
        "Activity",
        "Date & Time"
    ]]

    for log in logs:
        data.append([
            str(log["username"] or ""),
            str(log["activity"] or ""),
            str(log["activity_time"] or "")
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    content.append(table)

    pdf.build(content)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name='Activity_Log.pdf',
        mimetype='application/pdf'
    )
