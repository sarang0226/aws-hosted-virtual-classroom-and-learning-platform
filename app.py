from flask import Flask, render_template, request, redirect, url_for, flash, session
import boto3 as boto3
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "__YOUR_SECRET_KEY__" # 15-6-2025  updated 
app.permanent_session_lifetime = timedelta(minutes=15)  # Session timeout

# AWS S3 Config
S3_BUCKET = 'aws-project-virtualclassroom'
S3_REGION = 'eu-north-1'
s3 = boto3.client('s3', region_name=S3_REGION)

# Database Config
DB_HOST = '__YOUR_HOST_NAME__' 
DB_USER = 'admin'
DB_PASSWORD = 'Ram393'
DB_NAME = 'my-db'

def get_db_connection():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, cursorclass=pymysql.cursors.DictCursor)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['email']

        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            if e.args[0] == 1062:  # Duplicate entry error
                flash('Username already exists!', 'danger')
            else:
                flash(f"Error: {str(e)}", 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password'], password):  # Adjusted for dict cursor
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('content'))
            else:
                flash('Invalid credentials!', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('login.html')


@app.route('/content', methods=['GET', 'POST'])
def content():
    if 'username' not in session:
        flash('Please log in to access content!', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['file']
        if file:
            if file.content_length > 5 * 1024 * 1024:  # 5 MB size limit
                flash("File size exceeds limit!", 'danger')
            elif file.mimetype not in ['application/pdf', 'image/jpeg', 'image/png']:
                flash("Invalid file type!", 'danger')
            else:
                try:
                    s3.upload_fileobj(file, S3_BUCKET, file.filename)
                    flash(f"{file.filename} uploaded successfully!", 'success')
                except Exception as e:
                    flash(f"Error uploading file: {str(e)}", 'danger')

    try:
        files = s3.list_objects_v2(Bucket=S3_BUCKET).get('Contents', [])
    except Exception as e:
        files = []
        flash(f"Error fetching files: {str(e)}", 'danger')

    return render_template('content.html', files=files)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'info')
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
