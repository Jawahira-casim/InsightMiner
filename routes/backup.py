
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


# -----------------------------------------
# BACKUP PAGE
# -----------------------------------------

@backup_bp.route('/backup')
@role_required('Admin')
def backup_page():

    files = []

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                backup_name,
                file_size,
                created_by,
                created_at
            FROM backup_history
            ORDER BY created_at DESC, id DESC
        """)

        rows = cursor.fetchall()

        for row in rows:

            files.append({
                "name": row["backup_name"],
                "size": float(row["file_size"] or 0),
                "date": row["created_at"]
            })

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

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

    backup_buffer = BytesIO()

    with zipfile.ZipFile(
        backup_buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as backup:

        # Include available uploaded files and reports
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
server filesystem at the time of creation.

It does not contain a complete MySQL database dump.
"""

        backup.writestr(
            "backup_info.txt",
            info
        )

    # Read ZIP contents
    backup_buffer.seek(0)
    backup_data = backup_buffer.getvalue()

    file_size = round(
        len(backup_data) / 1024,
        2
    )

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO backup_history
            (backup_name, file_size, created_by, backup_data)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            sql,
            (
                backup_name,
                file_size,
                username,
                backup_data
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

    # Activity log
    log_activity(
        username,
        "Created system backup"
    )

    # Notification
    add_notification(
        username,
        "System backup created successfully."
    )

    # Download ZIP from memory
    return send_file(
        BytesIO(backup_data),
        mimetype="application/zip",
        as_attachment=True,
        download_name=backup_name
    )


# -----------------------------------------
# DOWNLOAD BACKUP FROM MYSQL
# -----------------------------------------

@backup_bp.route('/download_backup/<filename>')
@role_required('Admin')
def download_backup(filename):

    if (
        os.path.basename(filename) != filename
        or not filename.endswith(".zip")
    ):
        abort(400)

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT backup_data
            FROM backup_history
            WHERE backup_name = %s
        """, (filename,))

        result = cursor.fetchone()

        if not result or result[0] is None:
            return "Backup file not found.", 404

        backup_data = result[0]

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

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
        BytesIO(backup_data),
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename
    )


# -----------------------------------------
# DELETE BACKUP FROM MYSQL
# -----------------------------------------

@backup_bp.route('/delete_backup/<filename>')
@role_required('Admin')
def delete_backup(filename):

    if (
        os.path.basename(filename) != filename
        or not filename.endswith(".zip")
    ):
        abort(400)

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM backup_history
            WHERE backup_name = %s
        """, (filename,))

        deleted = cursor.rowcount

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

    username = session.get('username')

    if deleted and username:

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
