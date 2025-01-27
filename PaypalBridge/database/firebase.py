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



def rename_field(collection_name):
    """
    Renames 'name' field to 'username' in all documents of the specified collection
    
    Args:
        collection_name (str): Name of the collection to update
    """
    # Get reference to the collection
    collection_ref = db.collection(collection_name)
    
    # Get all documents
    docs = collection_ref.stream()
    
    # Batch write to handle multiple documents efficiently
    batch = db.batch()
    
    for doc in docs:
        doc_ref = collection_ref.document(doc.id)
        doc_data = doc.to_dict()
        
        # Check if the document has the 'name' field
        if 'name' in doc_data:
            # Create a new field with the old value
            batch.update(doc_ref, {
                'username': doc_data['name'],
                'name': firestore.DELETE_FIELD  # Delete the old field
            })
    
    # Commit the batch
    batch.commit()
    print("Field rename completed!")