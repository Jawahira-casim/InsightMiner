from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from db import get_connection
from activity import log_activity
from notification_helper import add_notification
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

dataset_history_bp = Blueprint('dataset_history', __name__)

@dataset_history_bp.route('/dataset_history')
def dataset_history():

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    uploaded_by = request.args.get('uploaded_by', '')
    date = request.args.get('date', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT *
        FROM datasets
        WHERE 1=1
    """

    params = []

    if search:
        sql += " AND filename LIKE %s"
        params.append(f"%{search}%")

    if category:
        sql += " AND category = %s"
        params.append(category)

    if uploaded_by:
        sql += " AND uploaded_by LIKE %s"
        params.append(f"%{uploaded_by}%")

    if date:
        sql += " AND DATE(upload_date) = %s"
        params.append(date)

    sql += " ORDER BY upload_date DESC"

    cursor.execute(sql, params)
    datasets = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM datasets WHERE category IS NOT NULL")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dataset_history.html",
        datasets=datasets,
        search=search,
        category=category,
        uploaded_by=uploaded_by,
        date=date,
        categories=categories
    )
@dataset_history_bp.route('/datasets_excel')
def datasets_excel():

    conn = get_connection()

    query = """
    SELECT
        filename,
        category,
        description,
        uploaded_by,
        rows_count,
        columns_count,
        upload_date
    FROM datasets
    ORDER BY upload_date DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    file_path = "static/dataset_history.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

@dataset_history_bp.route('/datasets_pdf')
def datasets_pdf():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        filename,
        category,
        description,
        uploaded_by,
        rows_count,
        columns_count,
        upload_date
    FROM datasets
    ORDER BY upload_date DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    pdf_path = "static/dataset_history.pdf"

    doc = SimpleDocTemplate(pdf_path)

    data = [[
        "Filename",
        "Category",
        "Description",
        "Uploaded By",
        "Rows",
        "Columns",
        "Upload Date"
    ]]

    for r in rows:
        data.append(list(r))

    table = Table(data)

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ('FONTSIZE',(0,0),(-1,-1),8),
    ]))

    doc.build([table])

    return send_file(pdf_path, as_attachment=True)
