from flask import Blueprint, render_template, send_file
import matplotlib.pyplot as plt
import shared

charts_bp = Blueprint('charts', __name__)


@charts_bp.route('/charts')
def charts():
    return render_template("charts.html")


@charts_bp.route('/generate_chart/<chart_type>')
def generate_chart(chart_type):

    if shared.current_df is None:
        return "Please upload a dataset first."

    numeric = shared.current_df.select_dtypes(include='number')

    if numeric.empty:
        return "No numeric columns available."

    plt.figure(figsize=(10, 6))

    # =========================
    # Histogram
    # =========================
    if chart_type == "hist":

        numeric.hist(
            figsize=(10, 8),
            color="#2563EB",
            edgecolor="black",
            linewidth=0.8
        )

        plt.suptitle(
            "Histogram Analysis",
            fontsize=18,
            fontweight="bold"
        )

        plt.tight_layout()

    # =========================
    # Bar Chart
    # =========================
    elif chart_type == "bar":

        numeric.mean().plot(
            kind="bar",
            color="#10B981",
            edgecolor="black"
        )

        plt.title(
            "Average Values",
            fontsize=18,
            fontweight="bold"
        )

        plt.xlabel("Columns")
        plt.ylabel("Average")

        plt.grid(axis="y", alpha=0.3)

    # =========================
    # Line Chart
    # =========================
    elif chart_type == "line":

        numeric.head(20).plot(
            linewidth=3,
            marker="o",
            markersize=6
        )

        plt.title(
            "Trend Analysis",
            fontsize=18,
            fontweight="bold"
        )

        plt.xlabel("Records")
        plt.ylabel("Values")

        plt.grid(True, alpha=0.3)

    # =========================
    # Pie Chart
    # =========================
    elif chart_type == "pie":

        colors = [
            "#2563EB",
            "#10B981",
            "#F59E0B",
            "#EF4444",
            "#8B5CF6",
            "#06B6D4",
            "#EC4899",
            "#84CC16"
        ]

        numeric.mean().plot(
            kind="pie",
            autopct="%1.1f%%",
            colors=colors
        )

        plt.title(
            "Distribution of Average Values",
            fontsize=18,
            fontweight="bold"
        )

        plt.ylabel("")

    # =========================
    # Scatter Plot
    # =========================
    elif chart_type == "scatter":

        cols = numeric.columns

        if len(cols) >= 2:

            plt.scatter(
                numeric[cols[0]],
                numeric[cols[1]],
                color="#2563EB",
                s=80,
                alpha=0.8,
                edgecolors="black"
            )

            plt.title(
                "Scatter Plot Analysis",
                fontsize=18,
                fontweight="bold"
            )

            plt.xlabel(cols[0])
            plt.ylabel(cols[1])

            plt.grid(True, alpha=0.3)

        else:
            return "Need at least two numeric columns."

    else:
        return "Invalid chart type."

    plt.tight_layout()

    plt.savefig(
        "static/chart.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return render_template("charts.html")


# =========================
# Download Chart
# =========================

@charts_bp.route('/download_chart')
def download_chart():

    return send_file(
        "static/chart.png",
        as_attachment=True,
        download_name="InsightMiner_Chart.png"
    )


# =========================
# Download Heatmap
# =========================

@charts_bp.route('/download_heatmap')
def download_heatmap():

    return send_file(
        "static/heatmap.png",
        as_attachment=True,
        download_name="InsightMiner_Heatmap.png"
    )