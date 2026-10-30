import zipfile
from flask import Blueprint, render_template, send_file, session, redirect, url_for
from decorators import role_required
from activity import log_activity
from notification_helper import add_notification
import os
import shutil
from datetime import datetime
from db import get_connection
backup_bp = Blueprint('backup', __name__)

BACKUP_FOLDER = "backups"


@backup_bp.route('/backup')
@role_required('Admin')
def backup_page():

    files = []

    if os.path.exists(BACKUP_FOLDER):
        for file in os.listdir(BACKUP_FOLDER):
            filepath = os.path.join(BACKUP_FOLDER, file)
            files.append({
                "name": file,
                "size": round(os.path.getsize(filepath) / 1024, 2),
                "date": datetime.fromtimestamp(os.path.getctime(filepath))
            })

    return render_template("backup.html", files=files)



@backup_bp.route('/create_backup')
@role_required('Admin')
def create_backup():

    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)

    backup_name = "insightminer_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip"
    backup_path = os.path.join(BACKUP_FOLDER, backup_name)

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as backup:

        # Backup uploaded datasets
        if os.path.exists("uploads"):
            for foldername, subfolders, filenames in os.walk("uploads"):
                for filename in filenames:
                    filepath = os.path.join(foldername, filename)
                    backup.write(filepath)

        # Backup reports
        if os.path.exists("reports"):
            for foldername, subfolders, filenames in os.walk("reports"):
                for filename in filenames:
                    filepath = os.path.join(foldername, filename)
                    backup.write(filepath)

        # Create backup information file
        info = f"""
InsightMiner System Backup

Created By : {session['username']}
Backup Date : {datetime.now()}

Backup completed successfully.
"""

        backup.writestr("backup_info.txt", info)

    # Get file size in KB
    file_size = round(os.path.getsize(backup_path) / 1024, 2)

    # Save backup details into MySQL
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO backup_history
    (backup_name, file_size, created_by)
    VALUES (%s, %s, %s)
    """

    cursor.execute(sql, (
    backup_name,
    file_size,
    session['username']
))
    conn.commit()
    cursor.close()
    conn.close()

    log_activity(session['username'], "Created system backup")
    add_notification(session['username'], "System backup created successfully.")

    return send_file(backup_path, as_attachment=True)

@backup_bp.route('/delete_backup/<filename>')
@role_required('Admin')
def delete_backup(filename):

    backup_path = os.path.join(BACKUP_FOLDER, filename)

    if os.path.exists(backup_path):
        os.remove(backup_path)

        if session.get('username'):
            log_activity(session['username'], f"Deleted backup: {filename}")

            add_notification(
                session['username'],
                f"Deleted backup '{filename}'."
            )

    return redirect(url_for('backup.backup_page'))

@backup_bp.route('/download_backup/<filename>')
@role_required('Admin')
def download_backup(filename):

    backup_path = os.path.join(BACKUP_FOLDER, filename)

    if os.path.exists(backup_path):

        log_activity(
            session['username'],
            f"Downloaded backup: {filename}"
        )

        add_notification(
            session['username'],
            f"Downloaded backup '{filename}'."
        )

        return send_file(
            backup_path,
            as_attachment=True
        )

    return "Backup file not found.", 404