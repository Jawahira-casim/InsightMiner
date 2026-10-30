from flask import Blueprint, render_template, request
from db import get_connection

comparison_bp = Blueprint('comparison', __name__)


@comparison_bp.route('/dataset_comparison')
def dataset_comparison():

    dataset1_id = request.args.get('dataset1')
    dataset2_id = request.args.get('dataset2')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, filename, rows_count, columns_count, upload_date
        FROM datasets
        ORDER BY upload_date DESC
    """)
    datasets = cursor.fetchall()

    ds1 = None
    ds2 = None
    error = None

    if dataset1_id and dataset2_id:

        if dataset1_id == dataset2_id:
            error = "Please select two different datasets."

        else:
            cursor.execute("SELECT * FROM datasets WHERE id=%s", (dataset1_id,))
            ds1 = cursor.fetchone()

            cursor.execute("SELECT * FROM datasets WHERE id=%s", (dataset2_id,))
            ds2 = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "dataset_comparison.html",
        datasets=datasets,
        ds1=ds1,
        ds2=ds2,
        error=error
    )