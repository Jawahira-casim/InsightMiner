from flask import Blueprint, render_template
from decorators import login_required

help_bp = Blueprint('help', __name__)

@help_bp.route('/help')
@login_required
def help_page():

    return render_template("help.html")