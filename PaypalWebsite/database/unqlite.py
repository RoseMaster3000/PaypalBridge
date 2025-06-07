# https://unqlite-python.readthedocs.io/en/stable/quickstart.html
from unqlite import UnQLite

# initialize database
db = UnQLite("DatabaseStorage/users.unqlite")
users = db.collection('users')
users.create()

# # get one user
# def fetch_user(username):
#     # UnQLite's filter method is similar to TinyDB's search
#     return users.filter(lambda x: x['username'] == username)

# # get all users
# def fetch_users():
#     data = users.all()
#     if data == None: data = []
#     return data

# # create new user
# def create_user(**kwargs):
#     if "username" not in kwargs:
#         raise Exception("USER must have a username")
#     users.store(kwargs)
 