from firebase_admin import credentials, initialize_app, firestore

cred = credentials.Certificate('firebaseKey.json')
initialize_app(cred)
db = firestore.client()

# get one user
def fetch_user(username):
    user = db.collection(u'users').where(u'username', u'==', username).limit(1).get()
    if not user:
        return None
    else:
        return user[0]

# get all users
def fetch_users():
    users_ref = db.collection(u'users')
    docs = users_ref.stream()
    users = []
    for doc in docs:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        users.append(user_data)
    return users

# create new user
def create_user(**kwargs):
    if "username" not in kwargs:
        raise Exception("USER must have a username")
    doc_ref = db.collection(u'users').document()
    doc_ref.set(kwargs)
    kwargs['username'] = kwargs['username']