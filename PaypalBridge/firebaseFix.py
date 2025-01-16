from firebase_admin import credentials, initialize_app, firestore

# database setup
cred = credentials.Certificate('FirebaseKey.json')
initialize_app(cred)
db = firestore.client()


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


if __name__ == '__main__':
    rename_field(u"users")