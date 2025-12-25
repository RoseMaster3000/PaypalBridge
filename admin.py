# -------STANDALONE UTILITY SCRIPT---------
# Run manually to create an ADMIN user in the database

import os
from flask import Flask
from flask_bcrypt import Bcrypt

# Import your existing TinyDB logic
from PaypalWebsite.database.tinydb import initialize_db, create_user

# -----------------------------------------
# 1. Create a minimal Flask app
# -----------------------------------------
app = Flask(__name__)

# Use the same secret key as your main app (optional but harmless)
app.config['SECRET_KEY'] = b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'

# -----------------------------------------
# 2. Set DATABASE_FOLDER exactly like main app
# -----------------------------------------
BASE_PATH = os.path.dirname(__file__)
app.config['DATABASE_FOLDER'] = os.path.join(BASE_PATH, "PaypalWebsite", "database")

# -----------------------------------------
# 3. Initialize bcrypt + TinyDB
# -----------------------------------------
bcrypt = Bcrypt(app)
initialize_db(app)   # <-- tinydb.py expects a Flask app, so we pass the app

# -----------------------------------------
# 4. Create admin user
# -----------------------------------------
def CreateAdmin():
    hashedPass = b'$2b$12$6Fjtz.GaNQlHwA1vOGCjP.pQeHWEiAij7T.4X3vR83/QN1S.Wg3u6'

    newUser = create_user(
        username="admin",
        email="admin@mail.com",
        password=hashedPass.decode('utf-8'),
        gems=0
    )

    if newUser is None:
        print("Could not create user")
    else:
        print("User has been created!")

# -----------------------------------------
# 5. Run
# -----------------------------------------
if __name__ == "__main__":
    CreateAdmin()