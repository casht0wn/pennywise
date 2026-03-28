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
_embedding_dimension = model.get_sentence_embedding_dimension()
labels = []
label_embeddings = np.empty((0, _embedding_dimension), dtype=np.float32)
_index_loaded = False


def refresh_label_index():
    """Rebuild in-memory label index from current transactions."""
    global labels, label_embeddings, _index_loaded

    label_data = session.query(Transaction.label).distinct().all()
    labels = [label[0] for label in label_data if label[0]]

    if labels:
        label_embeddings = model.encode(labels)
    else:
        label_embeddings = np.empty((0, _embedding_dimension), dtype=np.float32)

    _index_loaded = True
    return len(labels)


def _ensure_label_index_loaded():
    global _index_loaded
    if not _index_loaded:
        refresh_label_index()

def find_similar_labels(new_label, threshold=0.01):
    _ensure_label_index_loaded()

    if not new_label or not labels or label_embeddings.size == 0:
        return []

    new_embedding = model.encode([new_label])[0]

    new_norm = np.linalg.norm(new_embedding)
    if new_norm == 0:
        return []

    label_norms = np.linalg.norm(label_embeddings, axis=1)
    valid_norms = label_norms > 0
    if not np.any(valid_norms):
        return []

    similarities = np.zeros(len(labels), dtype=np.float32)
    similarities[valid_norms] = (
        (label_embeddings[valid_norms] @ new_embedding)
        / (label_norms[valid_norms] * new_norm)
    )

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

