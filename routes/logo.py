from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os

from decorators import role_required
from db import get_connection
from activity import log_activity

logo_bp = Blueprint('logo', __name__)

UPLOAD_FOLDER = "static/uploads"


@logo_bp.route('/logo', methods=['GET', 'POST'])
@role_required('Admin')
def logo():

    if request.method == "POST":

        file = request.files['logo']

        if file.filename != "":

            filename = secure_filename(file.filename)

            filepath = os.path.join(UPLOAD_FOLDER, filename)

            file.save(filepath)

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE system_settings
                SET setting_value=%s
                WHERE setting_key='logo'
            """, (f"uploads/{filename}",))

            conn.commit()

            cursor.close()
            conn.close()

            log_activity(session['username'], "Updated Institute Logo")

            flash("Institute logo updated successfully.", "success")

            return redirect(url_for('settings.settings'))

    return render_template("logo.html")