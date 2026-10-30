from flask import Blueprint, render_template, request, redirect, session

from dataset_processor import process_dataset
from activity import log_activity
from notification_helper import add_notification

import_dataset_bp = Blueprint("import_dataset", __name__)


@import_dataset_bp.route("/import_dataset", methods=["GET", "POST"])
def import_dataset():

    if request.method == "POST":

        file = request.files["dataset"]
        category = request.form.get("category")
        description = request.form.get("description")

        df, error = process_dataset(
            file,
            category,
            description,
            session.get("username")
        )

        if error:
            return error

        if session.get("username"):
            log_activity(session["username"], f"Imported external dataset '{file.filename}'")
            add_notification(session["username"], f"Imported external dataset '{file.filename}'.")

        return redirect("/dataset_history")

    return render_template("import_dataset.html")