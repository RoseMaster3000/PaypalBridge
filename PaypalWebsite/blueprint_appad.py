from flask_bcrypt import Bcrypt
from PaypalWebsite.database.tinydb import fetch_user
from flask import Blueprint, request, render_template, send_from_directory
from tinydb import TinyDB, Query
from werkzeug.utils import secure_filename
import os
import magic

appad = Blueprint("appad", __name__)
bcrypt = Bcrypt()

@appad.route('/forgot_appad_password', methods=['GET'])
def change_password():
    return "This feature does not exist yet..."

@appad.route('/upload_appad', methods=['POST'])
def upload_file():
    admin = fetch_user("admin")

    if not bcrypt.check_password_hash(admin['password'], request.form['password']):
        return "Incorrect password.", 403

    if 'file' not in request.files:
        return "No file part.", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file.", 400

    file_path = os.path.join(appad.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    mime = magic.Magic(mime=True)

    if mime.from_buffer(file.read(1024)) == 'text/plain':
        file.seek(0)
        file.save(file_path)
        return f"The file {file.filename} has been uploaded."
    else:
        return "Sorry, only text files are allowed.", 400

@appad.route('/remove_appad', methods=['POST'])
def remove_file():
    admin = fetch_user("admin")

    if not bcrypt.check_password_hash(admin['password'], request.form['password']):
        return "Incorrect password.", 403

    file_name = request.form.get('file_name', 'app-ads.txt')
    file_path = os.path.join(appad.config['UPLOAD_FOLDER'], secure_filename(file_name))

    if os.path.exists(file_path):
        os.remove(file_path)
        return f"The file '{file_name}' has been removed.", 200
    else:
        return f"The file '{file_name}' does not exist.", 404

@appad.route('/modify_appad', methods=['POST'])
def modify_file():
    admin = fetch_user("admin")

    if not bcrypt.check_password_hash(admin['password'], request.form['password']):
        return "Incorrect password.", 403

    file_path = os.path.join(appad.config['UPLOAD_FOLDER'], 'app-ads.txt')

    if os.path.exists(file_path):
        new_content = request.form.get('content', '')
        with open(file_path, 'w') as file:
            file.write(new_content)
        return "The file app-ads.txt has been modified."
    else:
        return "The file app-ads.txt does not exist.", 404

@appad.route('/app-ads.txt')
def serve_app_ads():
    return send_from_directory(appad.config['UPLOAD_FOLDER'], 'app-ads.txt')