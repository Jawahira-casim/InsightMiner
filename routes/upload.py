import shared
from flask import Blueprint, render_template, request, session
from activity import log_activity
import matplotlib.pyplot as plt
import seaborn as sns
from decorators import role_required
from notification_helper import add_notification
from dataset_processor import process_dataset

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['GET', 'POST'])
@role_required('Admin', 'Analyst')
def upload():

    if request.method == 'POST':

        file = request.files['file']

        if file:

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

            numeric_cols = df.select_dtypes(include='number').columns.tolist()

            correlation = df.select_dtypes(include='number').corr().round(2)

            if not correlation.empty:
                plt.figure(figsize=(8, 6))
                sns.heatmap(correlation, annot=True, cmap='coolwarm')
                plt.tight_layout()
                plt.savefig('static/heatmap.png')
                plt.close()

            df.hist(figsize=(10, 8))
            plt.tight_layout()
            plt.savefig('static/chart.png')
            plt.close()

            summary = f"""
            <a href="/clean_data">Remove Duplicate Records</a>
            <br><br>
            <a href="/download_report">Download Analysis Report</a>
            <br><br>
            <a href="/download_pdf">Download PDF Report</a>
            <br><br>

            <h2>Dataset Summary</h2>

            <h3>Dataset Information</h3>

            <table border="1" cellpadding="5">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Total Records</td>
                    <td>{rows}</td>
                </tr>
                <tr>
                    <td>Total Columns</td>
                    <td>{columns}</td>
                </tr>
                <tr>
                    <td>Numeric Columns</td>
                    <td>{len(numeric_cols)}</td>
                </tr>
                <tr>
                    <td>Total Missing Values</td>
                    <td>{missing.sum()}</td>
                </tr>
            </table>

            <br>

            <h3>Column Names</h3>
            <ul>
                {"".join([f"<li><a href='/column_info/{col}'>{col}</a></li>" for col in df.columns])}
            </ul>

            <h3>Numeric Columns</h3>
            <ul>
                {"".join([f"<li>{col}</li>" for col in numeric_cols])}
            </ul>

            <h3>Missing Values</h3>
            {missing.to_frame(name='Missing Count').to_html()}

            <h3>Statistical Summary</h3>
            {stats.to_html()}

            <h3>Correlation Matrix</h3>
            {correlation.to_html() if not correlation.empty else "No numeric columns available for correlation analysis."}

            <h3>Correlation Heatmap</h3>
            <img src="/static/heatmap.png" width="700">

            <h3>Data Visualization</h3>
            <img src="/static/chart.png" width="800">

            <h3>First 10 Rows</h3>
            {df.head(10).to_html()}
            """

            return render_template(
    "upload_result.html",
    rows=rows,
    columns=columns,
    numeric_cols=numeric_cols,
    missing=missing,
    stats=stats,
    correlation=correlation,
    df=df
)

    return render_template('upload.html')