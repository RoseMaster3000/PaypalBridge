from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from PaypalBridge.database.tinydb import initialize_db, create_user, fetch_user, fetch_users, update_user, delete_user
from PaypalBridge.decorators import login_required, anon_required, temp_required
from uuid import uuid4
import os

# initialize modules
app = Flask(__name__)
app.config['SECRET_KEY'] =  b'\xb4\xb5\xd0\xc5m\x10p\xdbB\xa2\xd4\x14'
bcrypt = Bcrypt(app)
initialize_db(app.root_path)

@app.before_request 
def verify_auth():
    session["replit"] = (os.environ["platform"] == "replit")
    if "username" not in session:
        generate_temp_user()


def generate_temp_user():
    user = create_user(
        username = str(uuid4()),
        email = None,
        password = str(uuid4()),
        gems = 0
    )
    session["username"] = user["username"]
    session["gems"] = user["gems"]
    
@app.route("/TempUser", methods=['POST'])
def temp_user():
    generate_temp_user()
    return "Temp User Generated<a href='/'>Go Back<a>"


# ask server for username
@app.route("/Identity", methods=['POST'])
def identity():
    return session.get("username", "[None]")


# debugger view (veiw/create users)
@app.route('/')
def index():
    # get all users
    users = fetch_users()
    # display page
    return render_template('index.html', users=users)


# 5 gems / 1 ad (5/1000)

# Create a new account
@app.route('/CreateUser', methods=['POST'])
@login_required
def CreateUser(user):
    # validate form
    if "" in request.form.values():
        return "Error: Please Fill All Fields!"
        
    # validate username (length)
    if len(request.form['username']) >= 36:
        return "Error: Username too long"

    # inherit gems from previous (temp) account
    if user["email"] == None:
        inheritedGems = user["gems"]
        delete_user(user["username"])       # (old) temp account
    else:
        inheritedGems = 0
    
    # store new user in database
    newUser = create_user(
        username = request.form['username'],
        email = request.form['email'],
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8'),
        gems = inheritedGems
    )
    if user==None:
        return "Could not create user"

    # log user in  
    session["username"] = request.form['username']
    session["gems"] = newUser["gems"]
    return f"User has been created!<br><a href='/'>Go Back<a>"


# Increment Gems
@app.route('/GetGem', methods=['POST'])
@login_required
def GetGem(user):
    user["gems"] += 1
    update_user(user["username"], **user)
    session["gems"] = user["gems"]
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# Increment Gems
@app.route('/GemCount')
@login_required
def GemCount(user):
    if user['gems'] == 1:
        return f"{user['gems']} Gem"
    else:
        return f"{user['gems']} Gems"


# TESTING PURPOSES ONLY
@app.route('/get_gem')
@login_required
def get_gem(user):
    if os.environ["platform"] == "replit":
        user["gems"] += 1
        update_user(user["username"], **user)
        session["gems"] = user["gems"]
        return redirect("/")
    else:
        return "This route only workes on REPLIT server."


# take over temp_user account (fake "registration")
@app.route('/Login', methods=['POST'])
@login_required
def login(user):
    
    newUser = fetch_user(request.form['username'])
    print(newUser)
    print(request.form['password'])
    print( bcrypt.check_password_hash(newUser['password'], request.form['password']))
    
    # verify user
    if newUser==None:
        return f"User Does not Exist<br><a href='/'>Go Back<a>"
    
    # verify password
    if not bcrypt.check_password_hash(newUser['password'], request.form['password']):
        return f"Password is Incorrect<br><a href='/'>Go Back<a>"

    # inherit gems from previous (temp) account
    if user["email"] == None:
        newUser["gems"] += user["gems"]
        update_user(newUser["username"], **newUser) # real account
        delete_user(user["username"])       # (old) temp account
    
    # log user in  
    session["username"] = newUser["username"]
    session["gems"] = newUser["gems"]
    return f"Logged in sucessful<br><a href='/'>Go Back<a>"


# delete multiple users 
@app.route('/DeleteUsers', methods=['POST'])
def delete_users():
    usernames = request.form.getlist('usernames') 
    for username in usernames: 
        session_check(username)
        delete_user(username) 
    return redirect('/')


# **New route to delete a user**
@app.route('/DeleteUser', methods=['POST'])
def delete_user_route():
    username = request.form['username']
    delete_user(username)
    session_check(username)
    return f"User [{username}] has been deleted<br><a href='/'>Go Back<a>"


# if you delete yourself, revoke the session 
def session_check(username):
    if "username" in session:
        if session["username"] == username:
            del session["username"]
            return

@app.route('/Logout', methods=['POST'])
def logout():
    session.pop("username", None)
    return f"You are logged out<br><a href='/'>Go Back<a>"


if __name__ == '__main__':
    app.run(debug=True)
