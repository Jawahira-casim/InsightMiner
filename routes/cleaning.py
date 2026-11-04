from io import StringIO
from flask import Blueprint, render_template, session
import pandas as pd
import shared
import json

from db import get_connection

cleaning_bp = Blueprint('cleaning', __name__)


@cleaning_bp.route('/clean_data')
def clean_data():

    username = session.get("username")

    if not username:
        return "Please log in first.", 401

    conn = get_connection()

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT data_json
            FROM insightminer_uploaded_data
            WHERE uploaded_by = %s
            ORDER BY id DESC
            LIMIT 1
        """, (username,))

        result = cursor.fetchone()

        if not result:
            return "No dataset uploaded."

        df = pd.read_json(
    StringIO(result["data_json"]),
    orient="split"
)
        # Before cleaning
        rows_before = df.shape[0]
        missing_before = df.isnull().sum().sum()

        # Remove duplicate records
        df = df.drop_duplicates()

        # Fill missing values
        for column in df.columns:

            if pd.api.types.is_numeric_dtype(df[column]):
                mean_value = df[column].mean()

                if pd.notna(mean_value):
                    df[column] = df[column].fillna(mean_value)

            else:
                df[column] = df[column].fillna("Unknown")

        # After cleaning
        rows_after = df.shape[0]
        missing_after = df.isnull().sum().sum()

        duplicates_removed = rows_before - rows_after

        # Save cleaned dataset back to MySQL
        cleaned_json = df.to_json(
            orient="split",
            date_format="iso"
        )

        cursor.execute("""
            UPDATE insightminer_uploaded_data
            SET data_json = %s
            WHERE uploaded_by = %s
            ORDER BY id DESC
            LIMIT 1
        """, (cleaned_json, username))

        conn.commit()

        shared.current_df = df

        return render_template(
            "clean_data.html",
            before_rows=rows_before,
            after_rows=rows_after,
            duplicates_removed=duplicates_removed,
            missing_before=missing_before,
            missing_after=missing_after
        )

    except Exception as e:
        conn.rollback()
        return f"Dataset cleaning failed: {str(e)}", 500

    finally:
        cursor.close()
        conn.close()
