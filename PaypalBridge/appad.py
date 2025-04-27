from PaypalBridge.website import app, bcrypt
from PaypalBridge.database.tinydb import *

from flask import Flask, request, render_template, send_from_directory
from tinydb import TinyDB, Query
from werkzeug.utils import secure_filename
import os
import magic


@app.route('/forgot_appad_password', methods=['GET'])
def change_password():
    return "This feature does not exist yet..."


# Upload txt.file to UPLOAD folder
@app.route('/upload_appad', methods=['POST'])
def upload_file():
    admin = fetch_user("admin")

    if not bcrypt.check_password_hash(admin['password'], request.form['password']):
        return "Incorrect password.", 403

    if 'file' not in request.files:
        return "No file part.", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file.", 400


    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    mime = magic.Magic(mime=True)
    
    # Validate MIME type
    if mime.from_buffer(file.read(1024)) == 'text/plain':
        file.seek(0)  # Reset file pointer after MIME check
        file.save(file_path)
        return f"The file {file.filename} has been uploaded."
    else:
        return "Sorry, only text files are allowed.", 400

@app.route('/remove_appad', methods=['POST'])
def remove_file():
    admin = fetch_user("admin")  # Fetch stored credentials

    if not bcrypt.check_password_hash(admin['password'], request.form['password']):
        return "Incorrect password.", 403

    file_name = request.form.get('file_name', 'app-ads.txt')  # Defaults to 'app-ads.txt'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file_name))

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return f"The file '{file_name}' has been removed.", 200
        except Exception:
            return "An error occurred while deleting the file.", 500
    else:
        return f"The file '{file_name}' does not exist.", 404

@app.route('/modify_appad', methods=['POST'])
def modify_file():
    admin = fetch_user("admin")  # Fetch stored credentials

    if not bcrypt.check_password_hash(admin['password'], request.form['password']):
        return "Incorrect password.", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'app-ads.txt')

    if os.path.exists(file_path):
        new_content = request.form.get('content', '')
        with open(file_path, 'w') as file:
            file.write(new_content)
        return "The file app-ads.txt has been modified."
    else:
        return "The file app-ads.txt does not exist.", 404


# make it publicly acccessible when visiting URL www.website.com/app-ads.txt
@app.route('/app-ads.txt') 
def serve_app_ads():
    return send_from_directory(app.config['UPLOAD_FOLDER'], 'app-ads.txt')
