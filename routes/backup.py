import io
import os
import csv
import json
import zipfile
import re
import shutil
import mysql.connector
from pathlib import PurePosixPath
from io import BytesIO, StringIO
from datetime import datetime, date, timezone, timedelta

from flask import (
    Blueprint, render_template, send_file, session,
    redirect, url_for, abort, request, flash
)

from decorators import role_required
from activity import log_activity
from notification_helper import add_notification
from db import get_connection


backup_bp = Blueprint("backup", __name__)

SRI_LANKA_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

BACKUP_TABLES = [
    "activity_logs",
    "datasets",
    "insightminer_uploaded_data",
    "notifications",
    "system_settings",
    "users",
    "backup_history"
]

EXCLUDED_COLUMNS = {
    "users": ["password"],
    "backup_history": ["backup_data"]
}


# --------------------------------------------------
# CSV VALUE CONVERSION
# --------------------------------------------------

def csv_value(value):

    if value is None:
        return ""

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)

    return value


# --------------------------------------------------
# EXPORT DATABASE TABLE TO CSV
# --------------------------------------------------

def export_table_to_csv(cursor, table_name):

    if table_name not in BACKUP_TABLES:
        raise ValueError("Invalid backup table name.")

    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    columns = cursor.fetchall()

    excluded = EXCLUDED_COLUMNS.get(table_name, [])

    column_names = [
        column[0]
        for column in columns
        if column[0] not in excluded
    ]

    if not column_names:
        return ""

    column_sql = ", ".join(
        f"`{column}`" for column in column_names
    )

    cursor.execute(
        f"SELECT {column_sql} FROM `{table_name}`"
    )

    rows = cursor.fetchall()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(column_names)

    for row in rows:
        writer.writerow([
            csv_value(value) for value in row
        ])

    return output.getvalue()


# --------------------------------------------------
# EXPORT UPLOADED DATASETS AS CSV
# --------------------------------------------------

def export_uploaded_datasets(cursor, backup):

    table_name = "insightminer_uploaded_data"

    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")

    column_names = [
        column[0] for column in cursor.fetchall()
    ]

    if "data_json" not in column_names:
        return

    cursor.execute(
        f"SELECT `data_json` FROM `{table_name}`"
    )

    rows = cursor.fetchall()

    for index, row in enumerate(rows, start=1):

        data_json = row[0]

        if not data_json:
            continue

        try:

            if isinstance(data_json, bytes):
                data_json = data_json.decode("utf-8")

            if isinstance(data_json, str):
                dataset = json.loads(data_json)
            else:
                dataset = data_json

            if not isinstance(dataset, dict):
                continue

            columns = dataset.get("columns", [])
            data = dataset.get("data", [])

            if not columns or not isinstance(data, list):
                continue

            output = StringIO()
            writer = csv.writer(output)

            writer.writerow(columns)

            for record in data:

                if isinstance(record, (list, tuple)):
                    writer.writerow(record)

                elif isinstance(record, dict):
                    writer.writerow([
                        record.get(column, "")
                        for column in columns
                    ])

            backup.writestr(
                f"uploaded_datasets/dataset_{index}.csv",
                output.getvalue()
            )

        except Exception as error:

            backup.writestr(
                f"uploaded_datasets/export_error_{index}.txt",
                str(error)
            )


# --------------------------------------------------
# BACKUP PAGE
# --------------------------------------------------

@backup_bp.route("/backup")
@role_required("Admin")
def backup_page():

    files = []

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                backup_name,
                file_size,
                created_by,
                created_at
            FROM backup_history
            ORDER BY created_at DESC, id DESC
        """)

        rows = cursor.fetchall()

        for row in rows:

            created_at = row["created_at"]

            if created_at:

                if created_at.tzinfo is None:
                    created_at = created_at.replace(
                        tzinfo=timezone.utc
                    )
                else:
                    created_at = created_at.astimezone(
                        timezone.utc
                    )

                date_utc = created_at.isoformat(
                    timespec="seconds"
                ).replace("+00:00", "Z")

            else:
                date_utc = ""

            files.append({
                "name": row["backup_name"],
                "size": float(row["file_size"] or 0),
                "date_utc": date_utc
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


# --------------------------------------------------
# CREATE COMPLETE SYSTEM BACKUP
# --------------------------------------------------

@backup_bp.route("/create_backup")
@role_required("Admin")
def create_backup():

    username = session.get("username")

    if not username:
        abort(403)

    # Generate filename using Sri Lanka local time.
    created_at_utc = datetime.now(timezone.utc)

    created_at_local = created_at_utc.astimezone(
        SRI_LANKA_TIMEZONE
    )

    backup_name = (
        "insightminer_backup_"
        + created_at_local.strftime("%Y%m%d_%H%M%S")
        + ".zip"
    )

    backup_buffer = BytesIO()

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # Get the currently connected database.
        cursor.execute("SELECT DATABASE()")
        database_result = cursor.fetchone()

        database_name = (
            database_result[0]
            if database_result and database_result[0]
            else None
        )

        if not database_name:
            raise RuntimeError(
                "Could not identify the connected database."
            )

        with zipfile.ZipFile(
            backup_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as backup:

            # ----------------------------------
            # 1. DATABASE TABLE CSV EXPORTS
            # ----------------------------------

            for table_name in BACKUP_TABLES:

                csv_data = export_table_to_csv(
                    cursor,
                    table_name
                )

                backup.writestr(
                    f"database/{table_name}.csv",
                    csv_data
                )

            # ----------------------------------
            # 2. DATABASE SQL SCHEMA
            # ----------------------------------

            schema_lines = [
                "-- InsightMiner database schema",
                f"CREATE DATABASE IF NOT EXISTS `{database_name}`;",
                f"USE `{database_name}`;",
                ""
            ]

            for table_name in BACKUP_TABLES:

                cursor.execute(
                    f"SHOW CREATE TABLE `{table_name}`"
                )

                result = cursor.fetchone()

                if result and len(result) > 1:

                    schema_lines.append(
                        result[1] + ";"
                    )

                    schema_lines.append("")

            backup.writestr(
                "database/database_schema.sql",
                "\n".join(schema_lines)
            )

            # ----------------------------------
            # 3. UPLOADED DATASETS
            # ----------------------------------

            export_uploaded_datasets(
                cursor,
                backup
            )

            # ----------------------------------
            # 4. LOCAL UPLOADS AND REPORTS
            # ----------------------------------

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

            # ----------------------------------
            # 5. BACKUP INFORMATION
            # ----------------------------------

            backup_info = f"""
InsightMiner Complete System Backup

Created By: {username}

Backup Filename: {backup_name}

Backup Date (Sri Lanka):
{created_at_local.strftime("%Y-%m-%d %H:%M:%S")}

Backup Date (UTC):
{created_at_utc.strftime("%Y-%m-%d %H:%M:%S")}

Database: {database_name}

Included database tables:
{chr(10).join("- " + table for table in BACKUP_TABLES)}

Included folders:
- uploads (if available)
- reports (if available)

Included files:
- Database table CSV exports
- Database SQL schema
- Uploaded dataset CSV exports
- Available uploaded files
- Available report files

Backup completed successfully.
"""

            backup.writestr(
                "backup_info.txt",
                backup_info
            )

        # ----------------------------------
        # 6. PREPARE ZIP DATA
        # ----------------------------------

        backup_buffer.seek(0)

        backup_data = backup_buffer.getvalue()

        file_size = round(
            len(backup_data) / 1024,
            2
        )

        # MySQL DATETIME stores a timezone-naive value.
        # Store UTC in the database.
        created_at_db = created_at_utc.replace(
            tzinfo=None
        )

        # ----------------------------------
        # 7. SAVE BACKUP INTO MYSQL
        # ----------------------------------

        cursor.execute("""
            INSERT INTO backup_history
            (
                backup_name,
                file_size,
                created_by,
                backup_data,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            backup_name,
            file_size,
            username,
            backup_data,
            created_at_db
        ))

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

    # ----------------------------------
    # 8. ACTIVITY LOG
    # ----------------------------------

    log_activity(
        username,
        "Created system backup"
    )

    # ----------------------------------
    # 9. NOTIFICATION
    # ----------------------------------

    add_notification(
        username,
        "System backup created successfully."
    )

    # ----------------------------------
    # 10. DOWNLOAD CREATED ZIP
    # ----------------------------------

    return send_file(
        BytesIO(backup_data),
        mimetype="application/zip",
        as_attachment=True,
        download_name=backup_name
    )


# --------------------------------------------------
# DOWNLOAD BACKUP FROM MYSQL
# --------------------------------------------------

@backup_bp.route("/download_backup/<filename>")
@role_required("Admin")
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

    username = session.get("username")

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


# --------------------------------------------------
# DELETE BACKUP FROM MYSQL
# --------------------------------------------------

@backup_bp.route("/delete_backup/<filename>")
@role_required("Admin")
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

    username = session.get("username")

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
        url_for("backup.backup_page")
    )

# ---------------------------------------------------------
# AUTOMATIC BACKUP RESTORE - ISOLATED TEST DATABASE
# ---------------------------------------------------------

RESTORE_TEST_DATABASE = "insightminer_restore_test4"

def get_restore_test_connection():
    """Connect only to the dedicated restore-test database."""

    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": RESTORE_TEST_DATABASE
    }

    if os.getenv("DB_SSL_REQUIRED", "false").lower() == "true":
        config["ssl_disabled"] = False
        ssl_ca = os.getenv("DB_SSL_CA")

        if ssl_ca:
            config["ssl_ca"] = ssl_ca
            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True

    return mysql.connector.connect(**config)


def validate_backup_zip(backup_zip):
    """Validate ZIP contents before accessing the database."""

    required_files = {
        f"database/{table}.csv" for table in BACKUP_TABLES
    }

    required_files.add("database/database_schema.sql")

    names = set(backup_zip.namelist())

    if not required_files.issubset(names):
        raise ValueError("The backup ZIP is missing required database files.")

    if len(names) > 1000:
        raise ValueError("The backup contains too many files.")

    total_size = sum(info.file_size for info in backup_zip.infolist())

    if total_size > 500 * 1024 * 1024:
        raise ValueError("The uncompressed backup exceeds the 500 MB limit.")

    allowed_prefixes = (
        "database/",
        "uploaded_datasets/",
        "uploads/",
        "reports/"
    )

    for info in backup_zip.infolist():

        name = info.filename

        if name == "backup_info.txt":
            continue

        if name.endswith("/"):
            name = name[:-1]

        path = PurePosixPath(name)

        if (
            not name
            or "\\" in name
            or path.is_absolute()
            or ".." in path.parts
            or ":" in name
        ):
            raise ValueError("Unsafe file path found in backup ZIP.")

        if not name.startswith(allowed_prefixes):
            raise ValueError("Unexpected file found in backup ZIP.")

        # Reject symbolic links.
        unix_mode = info.external_attr >> 16

        if (unix_mode & 0o170000) == 0o120000:
            raise ValueError("Symbolic links are not allowed in backups.")


def restore_csv_table(backup_zip, connection, table_name):
    """Import one CSV file into its corresponding database table."""

    cursor = connection.cursor()

    csv_path = f"database/{table_name}.csv"

    with backup_zip.open(csv_path) as csv_file:

        text_file = io.TextIOWrapper(
            csv_file,
            encoding="utf-8-sig",
            newline=""
        )

        reader = csv.DictReader(text_file)

        headers = reader.fieldnames

        if not headers:
            raise ValueError(f"CSV headers missing: {csv_path}")

        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")

        column_info = cursor.fetchall()

        column_types = {
            row[0]: row[1].lower()
            for row in column_info
        }

        if not set(headers).issubset(column_types):
            raise ValueError(f"Unexpected columns in {csv_path}")

        columns = ", ".join(f"`{column}`" for column in headers)

        placeholders = ", ".join(["%s"] * len(headers))

        sql = (
            f"INSERT INTO `{table_name}` ({columns}) "
            f"VALUES ({placeholders})"
        )

        restored_rows = 0

        for row in reader:

            values = []

            for column in headers:

                value = row.get(column)

                if value == "":
                    value = None

                column_type = column_types[column]

                if value is not None and (
                    column_type.startswith("datetime")
                    or column_type.startswith("timestamp")
                ):
                    value = datetime.fromisoformat(
                        value.replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                elif value is not None and column_type == "date":
                    value = date.fromisoformat(value)

                values.append(value)

            cursor.execute(sql, tuple(values))
            restored_rows += 1

    cursor.close()

    return restored_rows

def get_restore_staging_folder():
    """Return the isolated restore-test staging folder."""

    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    return os.path.join(
        project_root,
        "instance",
        "restore_test4_files"
    )
def restore_uploaded_files(backup_zip):
    """Copy uploaded files into an isolated staging folder."""

    restore_folder = get_restore_staging_folder()

    if os.path.exists(restore_folder):
        raise ValueError(
            "The restore staging folder already exists. "
            "Inspect or rename it before running another restore."
        )

    os.makedirs(restore_folder, exist_ok=True)

    copied_files = 0

    allowed_folders = (
        "uploaded_datasets/",
        "uploads/",
        "reports/"
    )

    for info in backup_zip.infolist():

        if not info.filename.startswith(allowed_folders):
            continue

        if info.is_dir():
            continue

        destination = os.path.join(
            restore_folder,
            *PurePosixPath(info.filename).parts
        )

        os.makedirs(os.path.dirname(destination), exist_ok=True)

        with backup_zip.open(info) as source:
            with open(destination, "wb") as target:
                shutil.copyfileobj(source, target)

        copied_files += 1

    return copied_files




@backup_bp.route("/restore_backup", methods=["POST"])
@role_required("Admin")
def restore_backup():

    uploaded_file = request.files.get("backup_file")

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a backup ZIP file.", "warning")
        return redirect("/backup")

    connection = None
    backup_zip = None
    created_tables = []

    try:

        # Validate ZIP archive
        if not zipfile.is_zipfile(uploaded_file.stream):
            raise ValueError(
                "The selected file is not a valid ZIP archive."
            )

        uploaded_file.stream.seek(0)

        backup_zip = zipfile.ZipFile(
            uploaded_file.stream,
            "r"
        )

        validate_backup_zip(backup_zip)

        # Check restore staging folder
        restore_folder = get_restore_staging_folder()

        if os.path.exists(restore_folder):
            raise ValueError(
                "The restore staging folder already exists. "
                "Inspect it before running another restore."
            )

        # Connect only to the isolated restore-test database
        connection = get_restore_test_connection()

        cursor = connection.cursor()

        cursor.execute("SHOW TABLES")
        existing_tables = cursor.fetchall()

        cursor.close()

        if existing_tables:
            raise ValueError(
                "The restore-test database is not empty. "
                "No data was restored. Use a fresh empty test database."
            )

        # Read database schema
        schema_sql = backup_zip.read(
            "database/database_schema.sql"
        ).decode("utf-8")

        table_statements = re.findall(
            r"CREATE TABLE\s+`([^`]+)`\s*\(.*?\)\s*ENGINE=.*?;",
            schema_sql,
            flags=re.IGNORECASE | re.DOTALL
        )

        if set(table_statements) != set(BACKUP_TABLES):
            raise ValueError(
                "The backup schema does not match the expected table list."
            )

        # Create database tables
        for table_name in BACKUP_TABLES:

            match = re.search(
                r"CREATE TABLE\s+`"
                + re.escape(table_name)
                + r"`\s*\(.*?\)\s*ENGINE=.*?;",
                schema_sql,
                flags=re.IGNORECASE | re.DOTALL
            )

            if not match:
                raise ValueError(
                    f"Table definition missing: {table_name}"
                )

            cursor = connection.cursor()

            cursor.execute(match.group(0))

            cursor.close()

            created_tables.append(table_name)

        connection.commit()

        # Restore CSV records
        restored_counts = {}

        for table_name in BACKUP_TABLES:

            restored_counts[table_name] = restore_csv_table(
                backup_zip,
                connection,
                table_name
            )

            connection.commit()

        # Close database connection before copying files
        connection.close()
        connection = None

        # Restore uploaded files into isolated staging folder
        copied_files = restore_uploaded_files(backup_zip)

        # Restoration success message
        total_rows = sum(restored_counts.values())

        flash(
            "Test restoration completed successfully. "
            f"Restored {total_rows} database rows "
            f"across {len(restored_counts)} tables and copied "
            f"{copied_files} files. "
            "The original database was not modified.",
            "success"
        )

        print("RESTORE TEST RESULTS:", restored_counts)

        return redirect("/backup")

    except Exception as error:

        print("RESTORE ERROR:", str(error))

        if connection and connection.is_connected():

            try:
                connection.rollback()

            except Exception as rollback_error:
                print("ROLLBACK ERROR:", str(rollback_error))

            # Remove only tables created by this restore attempt
            for table_name in reversed(created_tables):

                try:

                    cursor = connection.cursor()

                    cursor.execute(
                        f"DROP TABLE IF EXISTS `{table_name}`"
                    )

                    cursor.close()

                except Exception as cleanup_error:

                    print(
                        f"TABLE CLEANUP ERROR ({table_name}):",
                        str(cleanup_error)
                    )

            try:
                connection.commit()

            except Exception as cleanup_commit_error:

                print(
                    "CLEANUP COMMIT ERROR:",
                    str(cleanup_commit_error)
                )

        flash(
            "Restore failed: " + str(error),
            "danger"
        )

        return redirect("/backup")

    finally:

        if connection and connection.is_connected():
            connection.close()

        if backup_zip:
            backup_zip.close()
