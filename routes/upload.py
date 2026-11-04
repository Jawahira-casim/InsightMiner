
import shared
import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

from flask import Blueprint, render_template, request, session
from activity import log_activity
from decorators import role_required
from notification_helper import add_notification
from dataset_processor import process_dataset

upload_bp = Blueprint('upload', __name__)


def create_chart_image(fig):
    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png", bbox_inches="tight")
    plt.close(fig)

    image_buffer.seek(0)

    encoded_image = base64.b64encode(
        image_buffer.getvalue()
    ).decode("utf-8")

    return f"data:image/png;base64,{encoded_image}"


@upload_bp.route('/upload', methods=['GET', 'POST'])
@role_required('Admin', 'Analyst')
def upload():

    if request.method == 'POST':

        file = request.files.get('file')

        if not file or not file.filename:
            return "Please select a dataset file."

        df, error = process_dataset(
            file,
            "General",
            "Uploaded through Upload Dataset page",
            session.get("username")
        )

        if error:
            return error

        rows = df.shape[0]
        columns = df.shape[1]

        if session.get('username'):

            log_activity(
                session['username'],
                f"Uploaded dataset: {file.filename}"
            )

            add_notification(
                session['username'],
                f"Dataset '{file.filename}' uploaded successfully."
            )

        missing = df.isnull().sum()
        stats = df.describe().round(2)

        numeric_cols = df.select_dtypes(
            include='number'
        ).columns.tolist()

        correlation = df.select_dtypes(
            include='number'
        ).corr().round(2)

        heatmap_img = None
        chart_img = None

        # Generate correlation heatmap in memory
        if not correlation.empty:

            fig, ax = plt.subplots(figsize=(8, 6))

            sns.heatmap(
                correlation,
                annot=True,
                cmap='coolwarm',
                ax=ax
            )

            fig.tight_layout()

            heatmap_img = create_chart_image(fig)

        # Generate histograms in memory
        if numeric_cols:

            df[numeric_cols].hist(figsize=(10, 8))

            fig = plt.gcf()
            fig.tight_layout()

            chart_img = create_chart_image(fig)

        return render_template(
            "upload_result.html",
            rows=rows,
            columns=columns,
            numeric_cols=numeric_cols,
            missing=missing,
            stats=stats,
            correlation=correlation,
            df=df,
            heatmap_img=heatmap_img,
            chart_img=chart_img
        )

    return render_template('upload.html')
