from flask import Blueprint
import shared

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/column_info/<column_name>')
def column_info(column_name):

    if shared.current_df is None:
        return "No dataset uploaded."

    if column_name not in shared.current_df.columns:
        return "Column not found."

    col = shared.current_df[column_name]

    return f"""
    <h2>Column Information</h2>

    <p><b>Column:</b> {column_name}</p>
    <p><b>Data Type:</b> {col.dtype}</p>
    <p><b>Missing Values:</b> {col.isnull().sum()}</p>
    <p><b>Unique Values:</b> {col.nunique()}</p>

    <h3>Sample Values</h3>
    {col.head(10).to_frame().to_html()}

    <br>
    <a href="/upload">Back</a>
    """