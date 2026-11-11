
import os
from io import BytesIO

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from flask import (
    Blueprint,
    render_template,
    send_file,
    session,
    abort
)

import shared


charts_bp = Blueprint("charts", __name__)


# =========================================================
# Generate Chart Image in Memory
# =========================================================

def create_chart_image(chart_type):

    if shared.current_df is None:
        return None

    numeric = shared.current_df.select_dtypes(include="number")

    if numeric.empty:
        return None

    plt.close("all")

    # Histogram
    if chart_type == "hist":

        numeric.hist(
            figsize=(10, 8),
            color="#2563EB",
            edgecolor="black",
            linewidth=0.8
        )

        fig = plt.gcf()

        fig.suptitle(
            "Histogram Analysis",
            fontsize=18,
            fontweight="bold"
        )

    # Other chart types
    else:

        fig, ax = plt.subplots(figsize=(10, 6))

        # Bar Chart
        if chart_type == "bar":

            numeric.mean().plot(
                kind="bar",
                color="#10B981",
                edgecolor="black",
                ax=ax
            )

            ax.set_title(
                "Average Values",
                fontsize=18,
                fontweight="bold"
            )

            ax.set_xlabel("Columns")
            ax.set_ylabel("Average")
            ax.grid(axis="y", alpha=0.3)

        # Line Chart
        elif chart_type == "line":

            numeric.head(20).plot(
                linewidth=3,
                marker="o",
                markersize=6,
                ax=ax
            )

            ax.set_title(
                "Trend Analysis",
                fontsize=18,
                fontweight="bold"
            )

            ax.set_xlabel("Records")
            ax.set_ylabel("Values")
            ax.grid(True, alpha=0.3)

        # Pie Chart
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
                colors=colors,
                ax=ax
            )

            ax.set_title(
                "Distribution of Average Values",
                fontsize=18,
                fontweight="bold"
            )

            ax.set_ylabel("")

        # Scatter Plot
        elif chart_type == "scatter":

            cols = numeric.columns

            if len(cols) < 2:
                plt.close(fig)
                return None

            ax.scatter(
                numeric[cols[0]],
                numeric[cols[1]],
                color="#2563EB",
                s=80,
                alpha=0.8,
                edgecolors="black"
            )

            ax.set_title(
                "Scatter Plot Analysis",
                fontsize=18,
                fontweight="bold"
            )

            ax.set_xlabel(cols[0])
            ax.set_ylabel(cols[1])
            ax.grid(True, alpha=0.3)

        else:
            plt.close(fig)
            return None

    fig.tight_layout()

    # Save image into memory instead of static/chart.png
    image_buffer = BytesIO()

    fig.savefig(
        image_buffer,
        format="png",
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(fig)

    image_buffer.seek(0)

    return image_buffer


# =========================================================
# Charts Dashboard
# =========================================================

@charts_bp.route("/charts")
def charts():

    return render_template(
        "charts.html",
        chart_type=None
    )


# =========================================================
# Generate Chart
# =========================================================

@charts_bp.route("/generate_chart/<chart_type>")
def generate_chart(chart_type):

    allowed_types = [
        "hist",
        "bar",
        "line",
        "pie",
        "scatter"
    ]

    if chart_type not in allowed_types:
        abort(404)

    if shared.current_df is None:
        return "Please upload a dataset first.", 400

    image_buffer = create_chart_image(chart_type)

    if image_buffer is None:
        return "Unable to generate this chart. Check the numeric columns.", 400

    image_buffer.close()

    session["chart_type"] = chart_type

    return render_template(
        "charts.html",
        chart_type=chart_type
    )


# =========================================================
# Display Chart Image
# =========================================================

@charts_bp.route("/chart_image/<chart_type>")
def chart_image(chart_type):

    image_buffer = create_chart_image(chart_type)

    if image_buffer is None:
        abort(404)

    return send_file(
        image_buffer,
        mimetype="image/png"
    )


# =========================================================
# Download Chart
# =========================================================

@charts_bp.route("/download_chart")
def download_chart():

    chart_type = session.get("chart_type")

    if not chart_type:
        return "Please generate a chart first.", 400

    image_buffer = create_chart_image(chart_type)

    if image_buffer is None:
        return "Unable to generate chart.", 400

    return send_file(
        image_buffer,
        mimetype="image/png",
        as_attachment=True,
        download_name="InsightMiner_Chart.png"
    )


# =========================================================
# Download Heatmap
# =========================================================

@charts_bp.route("/download_heatmap")
def download_heatmap():

    heatmap_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "static",
        "heatmap.png"
    )

    if not os.path.isfile(heatmap_path):
        return "Heatmap image is not available.", 404

    return send_file(
        heatmap_path,
        mimetype="image/png",
        as_attachment=True,
        download_name="InsightMiner_Heatmap.png"
    )
