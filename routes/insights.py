from flask import Blueprint, render_template, session
import shared
from activity import log_activity
from decorators import role_required

insights_bp = Blueprint('insights', __name__)


@insights_bp.route('/insights')
@role_required('Admin', 'Analyst')
def insights():

    if shared.current_df is None:
        return "No dataset uploaded."

    df = shared.current_df

    rows = df.shape[0]
    columns = df.shape[1]

    numeric_count = len(df.select_dtypes(include='number').columns)
    categorical_count = len(df.select_dtypes(exclude='number').columns)

    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()

    total_cells = rows * columns
    missing_percentage = (missing / total_cells) * 100 if total_cells > 0 else 0
    duplicate_percentage = (duplicates / rows) * 100 if rows > 0 else 0

    quality_score = round(max(0, 100 - missing_percentage - duplicate_percentage), 2)

    if quality_score >= 90:
        quality_status = "Excellent"
    elif quality_score >= 75:
        quality_status = "Good"
    elif quality_score >= 50:
        quality_status = "Fair"
    else:
        quality_status = "Poor"

    trend_insights = []
    numeric_df = df.select_dtypes(include='number')

    if not numeric_df.empty:
        means = numeric_df.mean()

        highest_avg_col = means.idxmax()
        highest_avg_value = means.max()

        lowest_avg_col = means.idxmin()
        lowest_avg_value = means.min()

        trend_insights.append(
            f"'{highest_avg_col}' has the highest average value ({highest_avg_value:.2f})."
        )

        trend_insights.append(
            f"'{lowest_avg_col}' has the lowest average value ({lowest_avg_value:.2f})."
        )

        corr = numeric_df.corr().abs()
        corr_values = corr.where(~(corr == 1)).stack()

        if not corr_values.empty:
            pair = corr_values.idxmax()
            value = corr_values.max()

            trend_insights.append(
                f"Strongest relationship detected between '{pair[0]}' and '{pair[1]}' "
                f"with correlation {value:.2f}."
            )

        std_values = numeric_df.std()

        if not std_values.empty:
            max_std_col = std_values.idxmax()

            trend_insights.append(
                f"'{max_std_col}' shows the highest variation in the dataset."
            )

    else:
        trend_insights.append("No numeric columns available for trend analysis.")

    recommendations = []

    if missing > 0:
        recommendations.append("Handle missing values before prediction.")
    else:
        recommendations.append("No missing values detected.")

    if duplicates > 0:
        recommendations.append("Remove duplicate records for better model accuracy.")
    else:
        recommendations.append("No duplicate records detected.")

    if numeric_count == 0:
        recommendations.append("Machine learning requires numeric attributes.")

    if quality_score >= 90:
        recommendations.append(
            "Dataset is suitable for educational data analysis, predictive modelling, visualization, and professional report generation."
        )
    elif quality_score >= 75:
        recommendations.append(
            "Dataset is suitable for analysis. Minor cleaning may improve performance."
        )
    else:
        recommendations.append(
            "Clean the dataset before applying advanced analytics and prediction."
        )

    executive_summary = (
        f"This dataset contains {rows} records and {columns} columns. "
        f"It includes {numeric_count} numeric columns and {categorical_count} text columns. "
        f"The overall data quality score is {quality_score}% ({quality_status})."
    )

    if session.get('username'):
        log_activity(session['username'], "Viewed AI Insights")

    return render_template(
        "insights.html",
        rows=rows,
        columns=columns,
        numeric_count=numeric_count,
        categorical_count=categorical_count,
        missing=missing,
        duplicates=duplicates,
        quality_score=quality_score,
        quality_status=quality_status,
        trend_insights=trend_insights,
        recommendations=recommendations,
        executive_summary=executive_summary
    )