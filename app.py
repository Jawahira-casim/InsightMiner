import os
from dotenv import load_dotenv

load_dotenv()
from flask import Flask

from db import get_connection

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.dataset_history import dataset_history_bp
from routes.upload import upload_bp
from routes.cleaning import cleaning_bp
from routes.reports import reports_bp
from routes.charts import charts_bp
from routes.analysis import analysis_bp
from routes.prediction import prediction_bp
from routes.insights import insights_bp
from routes.profile import profile_bp
from routes.account import account_bp
from routes.activity_log import activity_log_bp
from routes.user_management import user_management_bp
from routes.settings import settings_bp
from routes.logo import logo_bp
from routes.dataset_comparison import comparison_bp
from routes.notifications import notifications_bp
from routes.backup import backup_bp
from routes.about import about_bp
from routes.help import help_bp
from routes.import_dataset import import_dataset_bp


app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not configured.")

# Register all Blueprints

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(dataset_history_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(cleaning_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(charts_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(account_bp)
app.register_blueprint(activity_log_bp)
app.register_blueprint(user_management_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(logo_bp)
app.register_blueprint(comparison_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(about_bp)
app.register_blueprint(help_bp)
app.register_blueprint(import_dataset_bp)


@app.context_processor
def notification_count():
    """
    Makes unread_notifications available
    in all HTML templates.
    """

    unread = 0
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM notifications
            WHERE is_read = FALSE
            """
        )

        result = cursor.fetchone()

        if result:
            unread = result[0]

    except Exception as error:
        print("Notification count error:", error)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return {
        "unread_notifications": unread
    }


if __name__ == "__main__":
    app.run(debug=True)