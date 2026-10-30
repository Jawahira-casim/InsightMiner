from flask import Blueprint, render_template
import pandas as pd
import shared

cleaning_bp = Blueprint('cleaning', __name__)


@cleaning_bp.route('/clean_data')
def clean_data():

    if shared.current_df is None:
        return "No dataset uploaded."

    # Before cleaning
    rows_before = shared.current_df.shape[0]
    missing_before = shared.current_df.isnull().sum().sum()

    # Remove duplicate rows
    shared.current_df.drop_duplicates(inplace=True)

    # Fill missing values
    for column in shared.current_df.columns:

        if pd.api.types.is_numeric_dtype(shared.current_df[column]):
            shared.current_df[column] = shared.current_df[column].fillna(
                shared.current_df[column].mean()
            )
        else:
            shared.current_df[column] = shared.current_df[column].fillna("Unknown")

    # After cleaning
    rows_after = shared.current_df.shape[0]
    missing_after = shared.current_df.isnull().sum().sum()
    duplicates_removed = rows_before - rows_after

    return render_template(
        "clean_data.html",
        before_rows=rows_before,
        after_rows=rows_after,
        duplicates_removed=duplicates_removed,
        missing_before=missing_before,
        missing_after=missing_after
    )