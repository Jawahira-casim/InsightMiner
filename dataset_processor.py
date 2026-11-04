
import os
import pandas as pd
import shared

from werkzeug.utils import secure_filename
from db import get_connection


def process_dataset(file, category="General", description="", uploaded_by=None):

    filename = secure_filename(file.filename or "")
    extension = os.path.splitext(filename)[1].lower()

    try:
        # Read the uploaded file directly without saving it to disk
        file.stream.seek(0)

        if extension == ".csv":
            df = pd.read_csv(file.stream)

        elif extension == ".xlsx":
            df = pd.read_excel(file.stream)

        else:
            return None, "Unsupported file format. Please upload CSV or XLSX."

        # Store the processed dataset for the application
        shared.current_df = df

        rows = df.shape[0]
        columns = df.shape[1]

        conn = get_connection()

        try:
            cursor = conn.cursor()

            sql = """
            INSERT INTO datasets
            (filename, rows_count, columns_count, category, description, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                sql,
                (
                    filename,
                    rows,
                    columns,
                    category,
                    description,
                    uploaded_by
                )
            )

            conn.commit()

        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

        return df, None

    except Exception as e:
        return None, f"Dataset processing failed: {str(e)}"
