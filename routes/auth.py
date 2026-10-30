from flask import Blueprint, render_template, request, redirect, session, url_for
from db import get_connection
from activity import log_activity
from werkzeug.security import generate_password_hash, check_password_hash
from notification_helper import add_notification
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()

        sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (username, hashed_password))
        conn.commit()

        cursor.close()
        conn.close()

        return "Registration Successful"

    return render_template('register.html')



@auth_bp.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == "" or password == "":
            return render_template(
                "login.html",
                error="Please enter username and password."
            )

        conn = get_connection()
        cursor = conn.cursor()

        sql = "SELECT * FROM users WHERE username=%s"
        cursor.execute(sql, (username,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):

            session['logged_in'] = True
            session['username'] = username
            session['role'] = user[3]

            log_activity(username, "User logged in")

            add_notification(
                username,
                "Logged into the system successfully."
            )

            return redirect(url_for('dashboard.dashboard'))

        else:
            return render_template(
                'login.html',
                error="Invalid Username or Password"
            )

    return render_template("login.html")
        
@auth_bp.route('/logout')
def logout():

    if session.get('username'):
     log_activity(session['username'], "User logged out")
    session.clear()
    return redirect(url_for('auth.login'))
        
        

    return render_template('login.html')