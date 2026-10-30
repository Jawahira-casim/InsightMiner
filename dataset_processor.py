import os
import pandas as pd
import shared

from db import get_connection


def process_dataset(file, category="General", description="", uploaded_by=None):

    filepath = os.path.join("uploads", file.filename)
    file.save(filepath)

    if file.filename.endswith(".csv"):
        df = pd.read_csv(filepath)

    elif file.filename.endswith(".xlsx"):
        df = pd.read_excel(filepath)

    else:
        return None, "Unsupported file format."

    shared.current_df = df

    rows = df.shape[0]
    columns = df.shape[1]

    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO datasets
    (filename, rows_count, columns_count, category, description, uploaded_by)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        sql,
        (
            file.filename,
            rows,
            columns,
            category,
            description,
            uploaded_by
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return df, None