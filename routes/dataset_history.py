
from flask import Blueprint, render_template, request, send_file
from db import get_connection
import pandas as pd

from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4


dataset_history_bp = Blueprint('dataset_history', __name__)


@dataset_history_bp.route('/dataset_history')
def dataset_history():

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    uploaded_by = request.args.get('uploaded_by', '')
    date = request.args.get('date', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
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

        cursor.execute(
            "SELECT DISTINCT category FROM datasets WHERE category IS NOT NULL"
        )
        categories = cursor.fetchall()

    finally:
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


# EXPORT DATASET HISTORY TO EXCEL
@dataset_history_bp.route('/datasets_excel')
def datasets_excel():

    conn = get_connection()

    try:
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

    finally:
        conn.close()

    # Generate Excel file in memory
    excel_buffer = BytesIO()

    df.to_excel(
        excel_buffer,
        index=False,
        engine="openpyxl"
    )

    excel_buffer.seek(0)

    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name="dataset_history.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# EXPORT DATASET HISTORY TO PDF
@dataset_history_bp.route('/datasets_pdf')
def datasets_pdf():

    conn = get_connection()
    cursor = conn.cursor()

    try:
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

    finally:
        cursor.close()
        conn.close()

    # Generate PDF file in memory
    pdf_buffer = BytesIO()

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4)
    )

    data = [[
        "Filename",
        "Category",
        "Description",
        "Uploaded By",
        "Rows",
        "Columns",
        "Upload Date"
    ]]

    for row in rows:
        data.append([
            str(value) if value is not None else ""
            for value in row
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    doc.build([table])

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="dataset_history.pdf",
        mimetype="application/pdf"
    )
