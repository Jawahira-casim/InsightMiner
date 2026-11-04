
import zipfile
import os
from io import BytesIO
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    send_file,
    session,
    redirect,
    url_for,
    abort
)

from decorators import role_required
from activity import log_activity
from notification_helper import add_notification
from db import get_connection


backup_bp = Blueprint('backup', __name__)

BACKUP_FOLDER = "backups"


# -----------------------------------------
# BACKUP PAGE
# -----------------------------------------

@backup_bp.route('/backup')
@role_required('Admin')
def backup_page():

    files = []

    # Vercel does not permanently store local files.
    # This folder is only used if it exists and is writable.
    if os.path.exists(BACKUP_FOLDER):

        for filename in os.listdir(BACKUP_FOLDER):

            filepath = os.path.join(BACKUP_FOLDER, filename)

            if os.path.isfile(filepath):

                files.append({
                    "name": filename,
                    "size": round(
                        os.path.getsize(filepath) / 1024, 2
                    ),
                    "date": datetime.fromtimestamp(
                        os.path.getctime(filepath)
                    )
                })

    return render_template(
        "backup.html",
        files=files
    )


# -----------------------------------------
# CREATE BACKUP
# -----------------------------------------

@backup_bp.route('/create_backup')
@role_required('Admin')
def create_backup():

    username = session.get('username')

    if not username:
        abort(403)

    created_at = datetime.now()

    backup_name = (
        "insightminer_backup_"
        + created_at.strftime("%Y%m%d_%H%M%S")
        + ".zip"
    )

    # Create ZIP file in memory
    backup_buffer = BytesIO()

    with zipfile.ZipFile(
        backup_buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as backup:

        # Include available uploaded datasets and reports
        for folder in ["uploads", "reports"]:

            if os.path.isdir(folder):

                for foldername, subfolders, filenames in os.walk(folder):

                    for filename in filenames:

                        filepath = os.path.join(
                            foldername,
                            filename
                        )

                        if os.path.isfile(filepath):

                            backup.write(
                                filepath,
                                arcname=filepath
                            )

        # Add backup information
        info = f"""
InsightMiner System Backup

Created By: {username}

Backup Date: {created_at}

Backup completed successfully.

Included folders:
- uploads (if available)
- reports (if available)

Note:
This backup contains files available in the
server filesystem at the time of backup.

It does not contain a complete MySQL database dump.
"""

        backup.writestr(
            "backup_info.txt",
            info
        )

    # Calculate backup size
    backup_buffer.seek(0)

    file_size = round(
        len(backup_buffer.getvalue()) / 1024,
        2
    )

    # Save backup history in MySQL
    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        INSERT INTO backup_history
        (backup_name, file_size, created_by)
        VALUES (%s, %s, %s)
        """

        cursor.execute(
            sql,
            (
                backup_name,
                file_size,
                username
            )
        )

        conn.commit()

    except Exception:

        if conn:
            conn.rollback()

        raise

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    # Record activity
    log_activity(
        username,
        "Created system backup"
    )

    # Send notification
    add_notification(
        username,
        "System backup created successfully."
    )

    # Download ZIP directly from memory
    backup_buffer.seek(0)

    return send_file(
        backup_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=backup_name
    )


# -----------------------------------------
# DELETE BACKUP
# -----------------------------------------

@backup_bp.route('/delete_backup/<filename>')
@role_required('Admin')
def delete_backup(filename):

    # Prevent directory traversal
    if (
        os.path.basename(filename) != filename
        or not filename.endswith(".zip")
    ):
        abort(400)

    backup_path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    if os.path.isfile(backup_path):

        os.remove(backup_path)

        username = session.get('username')

        if username:

            log_activity(
                username,
                f"Deleted backup: {filename}"
            )

            add_notification(
                username,
                f"Deleted backup '{filename}'."
            )

    return redirect(
        url_for('backup.backup_page')
    )


# -----------------------------------------
# DOWNLOAD EXISTING BACKUP
# -----------------------------------------

@backup_bp.route('/download_backup/<filename>')
@role_required('Admin')
def download_backup(filename):

    # Prevent directory traversal
    if (
        os.path.basename(filename) != filename
        or not filename.endswith(".zip")
    ):
        abort(400)

    backup_path = os.path.join(
        BACKUP_FOLDER,
        filename
    )

    if os.path.isfile(backup_path):

        username = session.get('username')

        log_activity(
            username,
            f"Downloaded backup: {filename}"
        )

        add_notification(
            username,
            f"Downloaded backup '{filename}'."
        )

        return send_file(
            backup_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename
        )

    return "Backup file not found.", 404
