from flask import Flask, request, render_template, send_from_directory
from tinydb import TinyDB, Query
from werkzeug.utils import secure_filename
import bcrypt
import os
import magic

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize TinyDB
db = TinyDB('tinydb.json')
settings = db.table('settings')

def get_password_from_db():
    result = settings.get(Query().key == 'app_ads_password')
    return result['password'].encode('utf-8') if result else None

def verify_password(input_password):
    stored_password = get_password_from_db()
    if stored_password:
        return bcrypt.checkpw(input_password.encode(), stored_password)
    return False

@app.route('/')
def home():
    return "Welcome to the home page!"

@app.route('/manage')
def manage():
    return render_template('index.html')

@app.route('/set_password', methods=['GET', 'POST'])
def set_password():
    if request.method == 'POST':
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        settings.upsert({'key': 'app_ads_password', 'password': hashed_password.decode()}, Query().key == 'app_ads_password')
        return "Password has been set successfully."
    return render_template('set_password.html')

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        if verify_password(current_password):
            new_hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
            settings.upsert({'key': 'app_ads_password', 'password': new_hashed_password.decode()}, Query().key == 'app_ads_password')
            return "Password has been changed successfully."
        else:
            return "Incorrect current password.", 403
    return render_template('change_password.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    password = request.form.get('password')
    if not verify_password(password):
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

@app.route('/remove', methods=['POST'])
def remove_file():
    password = request.form.get('password')
    if not verify_password(password):
        return "Incorrect password.", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'app-ads.txt')
    if os.path.exists(file_path):
        os.remove(file_path)
        return "The file app-ads.txt has been removed."
    else:
        return "The file app-ads.txt does not exist.", 404

@app.route('/modify', methods=['POST'])
def modify_file():
    password = request.form.get('password')
    if not verify_password(password):
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

if __name__ == '__main__':
    app.run(debug=True)