from io import BytesIO
import base64
import pandas as pd

from flask import Blueprint, send_file, session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image

)

import shared
from activity import log_activity
from decorators import role_required
from notification_helper import add_notification


reports_bp = Blueprint("reports", __name__)


# ---------------------------------------------------------
# Excel Report
# ---------------------------------------------------------

@reports_bp.route("/download_report")
@role_required("Admin", "Analyst", "Viewer")
def download_report():

    if shared.current_df is None:
        return "No dataset uploaded."

    

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        # ======================================
        # Dataset
        # ======================================

        shared.current_df.to_excel(
            writer,
            sheet_name="Dataset",
            index=False
        )

        # ======================================
        # Statistical Summary
        # ======================================

        shared.current_df.describe().round(2).to_excel(
            writer,
            sheet_name="Statistics"
        )

        # ======================================
        # Missing Values
        # ======================================

        missing_df = (
            shared.current_df
            .isnull()
            .sum()
            .reset_index()
        )

        missing_df.columns = [
            "Column",
            "Missing Values"
        ]

        missing_df.to_excel(
            writer,
            sheet_name="Missing Values",
            index=False
        )

        # ======================================
        # Correlation Matrix
        # ======================================

        numeric_df = shared.current_df.select_dtypes(
            include="number"
        )

        if not numeric_df.empty:

            numeric_df.corr().round(2).to_excel(
                writer,
                sheet_name="Correlation"
            )

        # ======================================
        # Latest Prediction Results
        # ======================================

        prediction = getattr(
            shared,
            "latest_prediction_result",
            None
        )

        if prediction:

            prediction_rows = [
                [
                    "Task Type",
                    prediction.get(
                        "task_type",
                        "N/A"
                    )
                ],
                [
                    "Algorithm",
                    prediction.get(
                        "algorithm_name",
                        "N/A"
                    )
                ],
                [
                    "Target Column",
                    prediction.get(
                        "target",
                        "N/A"
                    )
                ],
                [
                    "Training Records",
                    prediction.get(
                        "training_records",
                        "N/A"
                    )
                ],
                [
                    "Testing Records",
                    prediction.get(
                        "testing_records",
                        "N/A"
                    )
                ]
            ]

            # ----------------------------------
            # Regression
            # ----------------------------------

            if (
                prediction.get("task_type")
                == "regression"
            ):

                prediction_rows.extend([
                    [
                        "R² Score",
                        round(
                            prediction.get(
                                "r2",
                                0
                            ),
                            3
                        )
                    ],
                    [
                        "Mean Absolute Error",
                        round(
                            prediction.get(
                                "mae",
                                0
                            ),
                            3
                        )
                    ],
                    [
                        "Root Mean Squared Error",
                        round(
                            prediction.get(
                                "rmse",
                                0
                            ),
                            3
                        )
                    ],
                    [
                        "5-Fold CV R²",
                        round(
                            prediction.get(
                                "cv_score",
                                0
                            ),
                            3
                        )
                    ]
                ])

            # ----------------------------------
            # Classification
            # ----------------------------------

            elif (
                prediction.get("task_type")
                == "classification"
            ):

                prediction_rows.extend([
                    [
                        "Accuracy",
                        (
                            f"{prediction.get('accuracy', 0) * 100:.2f}%"
                        )
                    ],
                    [
                        "Precision",
                        round(
                            prediction.get(
                                "precision",
                                0
                            ),
                            3
                        )
                    ],
                    [
                        "Recall",
                        round(
                            prediction.get(
                                "recall",
                                0
                            ),
                            3
                        )
                    ],
                    [
                        "F1 Score",
                        round(
                            prediction.get(
                                "f1",
                                0
                            ),
                            3
                        )
                    ],
                    [
                        "5-Fold CV Accuracy",
                        (
                            f"{prediction.get('cv_score', 0) * 100:.2f}%"
                        )
                    ]
                ])

                if (
                    prediction.get("auc_score")
                    is not None
                ):

                    prediction_rows.append([
                        "ROC AUC Score",
                        round(
                            prediction.get(
                                "auc_score",
                                0
                            ),
                            3
                        )
                    ])

            # ----------------------------------
            # Feature Columns
            # ----------------------------------

            features = prediction.get(
                "features",
                []
            )

            if features:

                prediction_rows.append([
                    "Feature Columns",
                    ", ".join(
                        map(
                            str,
                            features
                        )
                    )
                ])

            # ----------------------------------
            # Model Interpretation
            # ----------------------------------

            interpretation = prediction.get(
                "interpretation",
                ""
            )

            if interpretation:

                prediction_rows.append([
                    "Model Interpretation",
                    interpretation
                ])

            prediction_df = pd.DataFrame(
                prediction_rows,
                columns=[
                    "Metric",
                    "Value"
                ]
            )

            prediction_df.to_excel(
                writer,
                sheet_name="Prediction Results",
                index=False
            )

            # ==================================
            # Confusion Matrix Sheet
            # ==================================

            if (
                prediction.get("task_type")
                == "classification"
            ):

                class_names = prediction.get(
                    "class_names",
                    []
                )

                confusion_rows = prediction.get(
                    "confusion_matrix_rows",
                    []
                )

                if (
                    class_names
                    and confusion_rows
                ):

                    confusion_values = [
                        row.get(
                            "values",
                            []
                        )
                        for row in confusion_rows
                    ]

                    confusion_df = pd.DataFrame(
                        confusion_values,
                        index=class_names,
                        columns=class_names
                    )

                    confusion_df.index.name = (
                        "Actual / Predicted"
                    )

                    confusion_df.to_excel(
                        writer,
                        sheet_name="Confusion Matrix"
                    )

                # ==============================
                # Classification Report Sheet
                # ==============================

                report_data = prediction.get(
                    "classification_report",
                    {}
                )

                if isinstance(
                    report_data,
                    dict
                ):

                    report_rows = []

                    for (
                        class_name,
                        metrics
                    ) in report_data.items():

                        if not isinstance(
                            metrics,
                            dict
                        ):
                            continue

                        if class_name in [
                            "accuracy",
                            "macro avg",
                            "weighted avg"
                        ]:
                            continue

                        report_rows.append({
                            "Class":
                                class_name,

                            "Precision":
                                round(
                                    metrics.get(
                                        "precision",
                                        0
                                    ),
                                    3
                                ),

                            "Recall":
                                round(
                                    metrics.get(
                                        "recall",
                                        0
                                    ),
                                    3
                                ),

                            "F1 Score":
                                round(
                                    metrics.get(
                                        "f1-score",
                                        0
                                    ),
                                    3
                                ),

                            "Support":
                                int(
                                    metrics.get(
                                        "support",
                                        0
                                    )
                                )
                        })

                    if report_rows:

                        classification_df = (
                            pd.DataFrame(
                                report_rows
                            )
                        )

                        classification_df.to_excel(
                            writer,
                            sheet_name=(
                                "Classification Report"
                            ),
                            index=False
                        )

            # ==================================
            # Format Prediction Results Sheet
            # ==================================

            prediction_sheet = writer.sheets[
                "Prediction Results"
            ]

            prediction_sheet.column_dimensions[
                "A"
            ].width = 28

            prediction_sheet.column_dimensions[
                "B"
            ].width = 90

            # Header bold
            for cell in prediction_sheet[1]:

                cell.font = cell.font.copy(
                    bold=True
                )

            # Wrap all text
            for row in prediction_sheet.iter_rows():

                for cell in row:

                    cell.alignment = (
                        cell.alignment.copy(
                            vertical="top",
                            wrap_text=True
                        )
                    )

            # Make interpretation row taller
            for row_number in range(
                1,
                prediction_sheet.max_row + 1
            ):

                metric_value = (
                    prediction_sheet.cell(
                        row=row_number,
                        column=1
                    ).value
                )

                if (
                    metric_value
                    == "Model Interpretation"
                ):

                    prediction_sheet.row_dimensions[
                        row_number
                    ].height = 90

        # ======================================
        # Basic Formatting for Other Sheets
        # ======================================

        for sheet_name in writer.sheets:

            worksheet = writer.sheets[
                sheet_name
            ]

            worksheet.freeze_panes = "A2"

            for cell in worksheet[1]:

                cell.font = cell.font.copy(
                    bold=True
                )

            for column_cells in worksheet.columns:

                max_length = 0

                column_letter = (
                    column_cells[0]
                    .column_letter
                )

                for cell in column_cells:

                    value = cell.value

                    if value is not None:

                        max_length = max(
                            max_length,
                            len(str(value))
                        )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max_length + 3,
                    45
                )

        # Keep Prediction Results wider
        if (
            "Prediction Results"
            in writer.sheets
        ):

            prediction_sheet = writer.sheets[
                "Prediction Results"
            ]

            prediction_sheet.column_dimensions[
                "A"
            ].width = 28

            prediction_sheet.column_dimensions[
                "B"
            ].width = 90

    # ==========================================
    # Finish Excel file
    # ==========================================

    output.seek(0)

    username = session.get(
        "username"
    )

    if username:

        log_activity(
            username,
            "Downloaded Excel report"
        )

        add_notification(
            username,
            "Generated Excel report."
        )

    return send_file(
        output,
        as_attachment=True,
        download_name="InsightMiner_Report.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )
# ---------------------------------------------------------
# PDF Report
# ---------------------------------------------------------

@reports_bp.route("/download_pdf")
@role_required("Admin", "Analyst", "Viewer")
def download_pdf():

    if shared.current_df is None:
        return "No dataset uploaded."

    df = shared.current_df

    output = BytesIO()

    pdf = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )

    styles = getSampleStyleSheet()

    content = []

    # -----------------------------------------------------
    # Title
    # -----------------------------------------------------

    content.append(
        Paragraph(
            "InsightMiner - Dataset Analysis Report",
            styles["Title"]
        )
    )

    content.append(
        Paragraph(
            "Imamath Foundation Professional Studies (IFPS) Institute",
            styles["Heading2"]
        )
    )

    content.append(
        Spacer(1, 16)
    )

    # -----------------------------------------------------
    # Dataset Summary
    # -----------------------------------------------------

    content.append(
        Paragraph(
            "Dataset Summary",
            styles["Heading2"]
        )
    )

    total_records = df.shape[0]
    total_columns = df.shape[1]

    numeric_columns = len(
        df.select_dtypes(
            include="number"
        ).columns
    )

    total_missing = int(
        df.isnull().sum().sum()
    )

    summary_data = [
        ["Item", "Value"],
        ["Total Records", total_records],
        ["Total Columns", total_columns],
        ["Numeric Columns", numeric_columns],
        ["Total Missing Values", total_missing]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            7 * cm,
            5 * cm
        ]
    )

    summary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#0d6efd")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )

    content.append(
        summary_table
    )

    content.append(
        Spacer(1, 16)
    )

    # -----------------------------------------------------
    # Column Names
    # -----------------------------------------------------

    content.append(PageBreak())

    content.append(
        Paragraph(
            "Column Names",
            styles["Heading2"]
        )
    )

    column_data = [
        ["No.", "Column Name"]
    ]

    for index, column in enumerate(
        df.columns,
        start=1
    ):
        column_data.append([
            index,
            str(column)
        ])

    column_table = Table(
        column_data,
        colWidths=[
            2 * cm,
            12 * cm
        ]
    )

    column_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#343a40")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            )
        ])
    )

    content.append(
        column_table
    )

    content.append(
        PageBreak()
    )

    # -----------------------------------------------------
    # Missing Values by Column
    # -----------------------------------------------------

    content.append(
        Paragraph(
            "Missing Values by Column",
            styles["Heading2"]
        )
    )

    missing_data = [
        ["Column", "Missing Count"]
    ]

    missing_series = df.isnull().sum()

    for column, count in missing_series.items():
        missing_data.append([
            str(column),
            int(count)
        ])

    missing_table = Table(
        missing_data,
        colWidths=[
            12 * cm,
            5 * cm
        ]
    )

    missing_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#ffc107")
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            )
        ])
    )

    content.append(
        missing_table
    )

    content.append(
        Spacer(1, 18)
    )

    # -----------------------------------------------------
    # Statistical Summary
    # -----------------------------------------------------

    numeric_df = df.select_dtypes(
        include="number"
    )

    if not numeric_df.empty:

        content.append(
            Paragraph(
                "Statistical Summary",
                styles["Heading2"]
            )
        )

        stats_df = (
            numeric_df
            .describe()
            .round(2)
            .reset_index()
        )

        stats_data = [
            [
                str(value)
                for value in stats_df.columns.tolist()
            ]
        ]

        for row in stats_df.values.tolist():
            stats_data.append([
                str(value)
                for value in row
            ])

        stats_table = Table(
            stats_data,
            repeatRows=1
        )

        stats_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#198754")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7
                )
            ])
        )

        content.append(
            stats_table
        )

        content.append(
            PageBreak()
        )

        # -------------------------------------------------
        # Correlation Matrix
        # -------------------------------------------------

        content.append(
            Paragraph(
                "Correlation Matrix",
                styles["Heading2"]
            )
        )

        corr_df = (
            numeric_df
            .corr()
            .round(2)
            .reset_index()
        )

        corr_data = [
            [
                str(value)
                for value in corr_df.columns.tolist()
            ]
        ]

        for row in corr_df.values.tolist():
            corr_data.append([
                str(value)
                for value in row
            ])

        corr_table = Table(
            corr_data,
            repeatRows=1
        )

        corr_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0dcaf0")
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    6
                )
            ])
        )

        content.append(
            corr_table
        )

    content.append(
        PageBreak()
    )

    # -----------------------------------------------------
    # First 10 Rows
    # -----------------------------------------------------

    content.append(
        Paragraph(
            "First 10 Rows",
            styles["Heading2"]
        )
    )

    first_rows = (
        df.head(10)
        .round(2)
    )

    first_rows_data = [
        [
            str(column)
            for column in first_rows.columns
        ]
    ]

    for row in first_rows.values.tolist():
        first_rows_data.append([
            str(value)
            for value in row
        ])

    first_rows_table = Table(
        first_rows_data,
        repeatRows=1
    )

    first_rows_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#6c757d")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.grey
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    content.append(
        first_rows_table
    )
    # ==========================================
# MACHINE LEARNING PREDICTION RESULTS
# ==========================================

    prediction = shared.latest_prediction_result

    if prediction:

        content.append(Spacer(1, 18))

    content.append(PageBreak())    

    content.append(
        Paragraph(
            "Machine Learning Prediction Results",
            styles["Heading2"]
        )
    )

    content.append(Spacer(1, 8))

    content.append(
        Paragraph(
            f"<b>Algorithm:</b> "
            f"{prediction['algorithm_name']}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Target Column:</b> "
            f"{prediction['target']}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Training Records:</b> "
            f"{prediction['training_records']}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Testing Records:</b> "
            f"{prediction['testing_records']}",
            styles["Normal"]
        )
    )

    content.append(Spacer(1, 10))

    # --------------------------------------
    # Regression
    # --------------------------------------

    if prediction["task_type"] == "regression":

        content.append(
            Paragraph(
                f"<b>R² Score:</b> "
                f"{prediction['r2']:.3f}",
                styles["Normal"]
            )
        )

        content.append(
            Paragraph(
                f"<b>Mean Absolute Error:</b> "
                f"{prediction['mae']:.3f}",
                styles["Normal"]
            )
        )

        content.append(
            Paragraph(
                f"<b>Root Mean Squared Error:</b> "
                f"{prediction['rmse']:.3f}",
                styles["Normal"]
            )
        )

        content.append(
            Paragraph(
                f"<b>5-Fold CV R²:</b> "
                f"{prediction['cv_score']:.3f}",
                styles["Normal"]
            )
        )

    # --------------------------------------
    # Classification
    # --------------------------------------

    elif prediction["task_type"] == "classification":

        # --------------------------------------
        # Classification Performance
        # --------------------------------------

        content.append(Spacer(1, 12))

        content.append(
            Paragraph(
                "Classification Performance",
                styles["Heading3"]
            )
        )

        performance_data = [
            ["Metric", "Value"],
            [
                "Accuracy",
                f"{prediction.get('accuracy', 0) * 100:.2f}%"
            ],
            [
                "Precision",
                f"{prediction.get('precision', 0):.3f}"
            ],
            [
                "Recall",
                f"{prediction.get('recall', 0):.3f}"
            ],
            [
                "F1 Score",
                f"{prediction.get('f1', 0):.3f}"
            ],
            [
                "5-Fold CV Accuracy",
                f"{prediction.get('cv_score', 0) * 100:.2f}%"
            ]
        ]

        performance_table = Table(
            performance_data,
            colWidths=[220, 120]
        )

        performance_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0d6efd")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6
                )
            ])
        )

        content.append(performance_table)

        # --------------------------------------
        # Target Classes
        # --------------------------------------

        class_names = prediction.get(
            "class_names",
            []
        )

        if class_names:

            content.append(Spacer(1, 12))

            content.append(
                Paragraph(
                    "Target Classes",
                    styles["Heading3"]
                )
            )

            content.append(
                Paragraph(
                    ", ".join(
                        map(str, class_names)
                    ),
                    styles["Normal"]
                )
            )

                # --------------------------------------
        # Confusion Matrix
        # --------------------------------------

        confusion_rows = prediction.get(
            "confusion_matrix_rows",
            []
        )

        class_names = prediction.get(
            "class_names",
            []
        )

        if confusion_rows and class_names:

            content.append(Spacer(1, 12))

            content.append(
                Paragraph(
                    "Confusion Matrix",
                    styles["Heading3"]
                )
            )

            confusion_data = [
                ["Actual / Predicted"]
                + [str(name) for name in class_names]
            ]

            for row in confusion_rows:

                actual_class = row.get(
                    "actual_class",
                    ""
                )

                values = row.get(
                    "values",
                    []
                )

                confusion_data.append(
                    [str(actual_class)]
                    + [str(value) for value in values]
                )

            confusion_table = Table(
                confusion_data,
                repeatRows=1
            )

            confusion_table.setStyle(
                TableStyle([
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#343a40")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (0, -1),
                        "Helvetica-Bold"
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),
                    (
                        "PADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    )
                ])
            )

            content.append(
                confusion_table
            )

               # --------------------------------------
        # Classification Report
        # --------------------------------------

        classification_report_data = prediction.get(
            "classification_report",
            []
        )

        if classification_report_data:

            content.append(Spacer(1, 12))

            content.append(
                Paragraph(
                    "Classification Report",
                    styles["Heading3"]
                )
            )

            report_data = [
                [
                    "Class",
                    "Precision",
                    "Recall",
                    "F1 Score",
                    "Support"
                ]
            ]

            # ----------------------------------
            # If report is a dictionary
            # ----------------------------------

            if isinstance(
                classification_report_data,
                dict
            ):

                for class_name, metrics in (
                    classification_report_data.items()
                ):

                    # Skip summary values
                    if not isinstance(metrics, dict):
                        continue

                    # Skip overall summary rows
                    if class_name in [
                        "accuracy",
                        "macro avg",
                        "weighted avg"
                    ]:
                        continue

                    report_data.append([
                        str(class_name),

                        f"{metrics.get('precision', 0):.3f}",

                        f"{metrics.get('recall', 0):.3f}",

                        f"{metrics.get('f1-score', 0):.3f}",

                        str(
                            int(
                                metrics.get(
                                    "support",
                                    0
                                )
                            )
                        )
                    ])

            # ----------------------------------
            # If report is a list
            # ----------------------------------

            elif isinstance(
                classification_report_data,
                list
            ):

                for row in classification_report_data:

                    # Dictionary row
                    if isinstance(row, dict):

                        class_name = row.get(
                            "class",
                            row.get(
                                "label",
                                ""
                            )
                        )

                        precision = row.get(
                            "precision",
                            0
                        )

                        recall = row.get(
                            "recall",
                            0
                        )

                        f1 = row.get(
                            "f1_score",
                            row.get(
                                "f1-score",
                                0
                            )
                        )

                        support = row.get(
                            "support",
                            0
                        )

                        report_data.append([
                            str(class_name),
                            f"{precision:.3f}",
                            f"{recall:.3f}",
                            f"{f1:.3f}",
                            str(int(support))
                        ])

            # ----------------------------------
            # Create table only if data exists
            # ----------------------------------

            if len(report_data) > 1:

                report_table = Table(
                    report_data,
                    colWidths=[
                        90,
                        75,
                        75,
                        75,
                        65
                    ]
                )

                report_table.setStyle(
                    TableStyle([
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#198754")
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.white
                        ),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, 0),
                            "Helvetica-Bold"
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.grey
                        ),
                        (
                            "ALIGN",
                            (1, 1),
                            (-1, -1),
                            "CENTER"
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE"
                        ),
                        (
                            "PADDING",
                            (0, 0),
                            (-1, -1),
                            5
                        )
                    ])
                )

                content.append(
                    report_table
                )

                        # --------------------------------------
        # ROC Curve
        # --------------------------------------

        roc_image = prediction.get(
            "roc_image"
        )

        auc_score = prediction.get(
            "auc_score"
        )

        roc_message = prediction.get(
            "roc_message"
        )

        if roc_image:

            content.append(Spacer(1, 12))

            content.append(
                Paragraph(
                    "ROC Curve",
                    styles["Heading3"]
                )
            )

            if auc_score is not None:

                content.append(
                    Paragraph(
                        f"<b>ROC AUC Score:</b> "
                        f"{auc_score:.3f}",
                        styles["Normal"]
                    )
                )

                content.append(
                    Spacer(1, 8)
                )

            

            image_bytes = base64.b64decode(
                roc_image
            )

            roc_buffer = BytesIO(
                image_bytes
            )

            roc_pdf_image = Image(
                roc_buffer,
                width=14 * cm,
                height=9 * cm
            )

            content.append(
                roc_pdf_image
            )

        elif roc_message:

            content.append(Spacer(1, 12))

            content.append(
                Paragraph(
                    "ROC Curve",
                    styles["Heading3"]
                )
            )

            content.append(
                Paragraph(
                    roc_message,
                    styles["Normal"]
                )
            )
    # --------------------------------------
    # Model Interpretation
    # --------------------------------------

    content.append(Spacer(1, 12))

    content.append(
        Paragraph(
            "Model Interpretation",
            styles["Heading3"]
        )
    )

    content.append(
        Paragraph(
            prediction["interpretation"],
            styles["Normal"]
        )
    )

    # -----------------------------------------------------
    # Build PDF
    # -----------------------------------------------------

    pdf.build(
        content
    )

    output.seek(0)

    username = session.get("username")

    if username:

        log_activity(
            username,
            "Downloaded PDF report"
        )

        add_notification(
            username,
            "Generated PDF report."
        )

    return send_file(
        output,
        as_attachment=True,
        download_name="InsightMiner_Report.pdf",
        mimetype="application/pdf"
    )