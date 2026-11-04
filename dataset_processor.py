
import os
import pandas as pd
import shared

from db import get_connection
from werkzeug.utils import secure_filename


def process_dataset(file, category="General", description="", uploaded_by=None):

    filename = secure_filename(file.filename or "")
    extension = os.path.splitext(filename)[1].lower()

    try:
        file.stream.seek(0)

        if extension == ".csv":
            df = pd.read_csv(file.stream)

        elif extension == ".xlsx":
            df = pd.read_excel(file.stream)

        else:
            return None, "Unsupported file format. Please upload CSV or XLSX."

        shared.current_df = df

        rows = df.shape[0]
        columns = df.shape[1]

        # Serialize dataset for persistent MySQL storage
        data_json = df.to_json(
            orient="split",
            date_format="iso"
        )

        conn = get_connection()

        try:
            cursor = conn.cursor()

            # Create persistent dataset storage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insightminer_uploaded_data (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    uploaded_by VARCHAR(255) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    data_json LONGTEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_uploaded_user (uploaded_by)
                )
            """)

            # Save dataset information
            cursor.execute("""
                INSERT INTO datasets
                (filename, rows_count, columns_count, category, description, uploaded_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                filename,
                rows,
                columns,
                category,
                description,
                uploaded_by
            ))

            # Save the actual dataset
            cursor.execute("""
                INSERT INTO insightminer_uploaded_data
                (uploaded_by, filename, data_json)
                VALUES (%s, %s, %s)
            """, (
                uploaded_by or "",
                filename,
                data_json
            ))

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()

        return df, None

    except Exception as e:
        return None, f"Dataset processing failed: {str(e)}"
