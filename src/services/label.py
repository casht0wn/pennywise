import numpy as np
from sentence_transformers import SentenceTransformer
from services.db import session, Category, Transaction

"""
Use the transaction labels to determine recurring payees by using sentence similarity.
This can help to auto-fill the payee field for new transactions based on their labels.
For example, if a transaction label is "Starbucks #1234" and there is an existing transaction
with the label "Starbucks #5678", we can suggest "Starbucks" as the payee based on the similarity
of the labels. The common part "Starbucks" indicates they are likely from the same payee.
"""

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
label_data = session.query(Transaction.label).distinct().all()
labels = [label[0] for label in label_data if label[0] is not None]
label_embeddings = model.encode(labels)

def find_similar_labels(new_label, threshold=0.01):
    new_embedding = model.encode([new_label])[0]
    similarities = (label_embeddings @ new_embedding) / (np.linalg.norm(label_embeddings, axis=1) * np.linalg.norm(new_embedding))
    similar_labels = [(labels[i], similarities[i]) for i in range(len(labels)) if similarities[i] >= threshold]
    similar_labels.sort(key=lambda x: x[1], reverse=True)
    return similar_labels

def suggest_payee(new_label):
    similar_labels = find_similar_labels(new_label)
    if not similar_labels:
        return None
    
    # Get the most similar label
    most_similar_label = similar_labels[0][0]
    
    # Find the payee associated with this label
    transaction = session.query(Transaction).filter_by(label=most_similar_label).first()
    if transaction and transaction.payee:
        return transaction.payee
    
    return None

def assign_payee_to_transaction(transaction_id, new_label):
    transaction = session.query(Transaction).get(transaction_id)
    if not transaction:
        return False
    
    suggested_payee = suggest_payee(new_label)
    if suggested_payee:
        transaction.payee = suggested_payee
        session.commit()
        return True
    
    return False

