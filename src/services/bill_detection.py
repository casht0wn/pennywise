"""
Bill Detection Service

Analyzes transactions to detect recurring bill patterns using:
- Payee name similarity (using existing ML from label.py)
- Amount within ±10% tolerance
- Same day of month (±3 days)
- Manual confirmation required

Returns suggestions for user review before creating bills.
"""

from datetime import datetime, date
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional
from dateutil.relativedelta import relativedelta

from services.db import session, Transaction, Bill, BillInstance
from services.label import find_similar_labels

@dataclass
class BillSuggestion:
    """Represents a suggested recurring bill detected from transaction patterns"""
    payee: str
    expected_amount: float
    due_day: int
    frequency: str
    confidence: float
    supporting_transactions: List[Transaction]
    category_id: Optional[int] = None

def normalize_payee_from_label(label: str) -> str:
    """Extract normalized payee name from transaction label"""
    import re
    
    # First, more aggressive normalization for better matching
    # Remove transaction IDs, store numbers, locations, dates, special chars
    cleaned = re.sub(r'#\d+', '', label)  # Remove #1234 patterns
    cleaned = re.sub(r'\*\d+', '', cleaned)  # Remove *1234 patterns  
    cleaned = re.sub(r'\b\d{3,}\b', '', cleaned)  # Remove 3+ digit numbers (store IDs, etc)
    cleaned = re.sub(r'\b(STORE|LOC|LOCATION)\s*\d+\b', '', cleaned, re.IGNORECASE)
    cleaned = re.sub(r'\b\d{1,2}/\d{1,2}(/\d{2,4})?\b', '', cleaned)  # Remove dates
    cleaned = re.sub(r'[*\-_]+', ' ', cleaned)  # Replace special chars with spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Normalize spaces
    
    # Use existing similarity matching with cleaned label
    similar_labels = find_similar_labels(cleaned, threshold=0.4)  # Lower threshold for better matching
    
    if similar_labels:
        # Find existing payee from most similar transaction
        similar_label = similar_labels[0][0]
        transaction = session.query(Transaction).filter_by(label=similar_label).first()
        if transaction and transaction.payee:
            return transaction.payee
    
    # Fallback: extract base company name from cleaned label
    # Take first 2-3 meaningful words (skip common prefixes)
    words = [w for w in cleaned.split() if len(w) > 2 and not w.isdigit()]
    
    # Skip common payment prefixes
    skip_words = {'ACH', 'DEBIT', 'CREDIT', 'CARD', 'PURCHASE', 'PAYMENT', 'TRANSFER', 'WITHDRAWAL'}
    meaningful_words = [w for w in words if w.upper() not in skip_words]
    
    if meaningful_words:
        return ' '.join(meaningful_words[:2])  # Take first 2 meaningful words
    elif words:
        return ' '.join(words[:3])  # Fallback to first 3 words
    else:
        return label.strip()  # Last resort

def group_transactions_by_payee() -> Dict[str, List[Transaction]]:
    """Group all transactions by normalized payee name"""
    payee_groups = defaultdict(list)
    
    # Get all transactions with amounts (skip zero amounts)
    transactions = session.query(Transaction).filter(
        Transaction.amount != 0
    ).order_by(Transaction.date).all()
    
    print(f"Processing {len(transactions)} transactions for bill detection...")
    
    for transaction in transactions:
        # Use existing payee if set, otherwise normalize from label
        if transaction.payee:
            payee = transaction.payee
        else:
            payee = normalize_payee_from_label(transaction.label)
            # Store normalized payee back to transaction for future use
            transaction.payee = payee
        
        payee_groups[payee].append(transaction)
    
    # Commit any payee updates
    try:
        session.commit()
    except:
        session.rollback()
    
    print(f"Grouped into {len(payee_groups)} unique payees")
    return payee_groups

def detect_monthly_pattern(transactions: List[Transaction]) -> Optional[BillSuggestion]:
    """Detect monthly recurring pattern in transaction list"""
    if len(transactions) < 3:  # Need at least 3 occurrences to establish pattern
        return None
    
    # Sort by date
    transactions.sort(key=lambda t: t.date)
    
    # Check for monthly frequency (transactions roughly 30 days apart)
    monthly_candidates = []
    
    for i in range(len(transactions) - 2):
        t1, t2, t3 = transactions[i], transactions[i+1], transactions[i+2]
        
        # Check if intervals are roughly monthly (25-35 days)
        interval1 = (t2.date - t1.date).days
        interval2 = (t3.date - t2.date).days
        
        if 25 <= interval1 <= 35 and 25 <= interval2 <= 35:
            monthly_candidates.extend([t1, t2, t3])
    
    if len(monthly_candidates) < 3:
        return None
    
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for t in monthly_candidates:
        if t.id not in seen:
            seen.add(t.id)
            unique_candidates.append(t)
    
    # Check amount consistency (within ±10%)
    amounts = [abs(t.amount) for t in unique_candidates]
    avg_amount = sum(amounts) / len(amounts)
    
    consistent_amounts = []
    for t in unique_candidates:
        amount = abs(t.amount)
        if avg_amount * 0.9 <= amount <= avg_amount * 1.1:
            consistent_amounts.append(t)
    
    if len(consistent_amounts) < 3:
        return None
    
    # Check day-of-month consistency (±3 days)
    days = [t.date.day for t in consistent_amounts]
    avg_day = sum(days) / len(days)
    
    consistent_day_transactions = []
    for t in consistent_amounts:
        if abs(t.date.day - avg_day) <= 3:
            consistent_day_transactions.append(t)
    
    if len(consistent_day_transactions) < 3:
        return None
    
    # Calculate confidence based on consistency
    confidence = min(1.0, len(consistent_day_transactions) / 5.0)  # Higher confidence with more occurrences
    
    # Get the payee name
    payee = consistent_day_transactions[0].payee or normalize_payee_from_label(
        consistent_day_transactions[0].label
    )
    
    return BillSuggestion(
        payee=payee,
        expected_amount=round(avg_amount, 2),
        due_day=int(round(avg_day)),
        frequency='monthly',
        confidence=confidence,
        supporting_transactions=consistent_day_transactions,
        category_id=consistent_day_transactions[0].category_id
    )

def detect_potential_bills() -> List[BillSuggestion]:
    """
    Scan all transactions to detect potential recurring bills
    Returns list of suggestions for user review
    """
    suggestions = []
    payee_groups = group_transactions_by_payee()
    
    for payee, transactions in payee_groups.items():
        if len(transactions) >= 3:  # Need minimum occurrences
            # Try to detect monthly pattern
            monthly_pattern = detect_monthly_pattern(transactions)
            if monthly_pattern:
                # Check if bill already exists for this payee
                existing_bill = session.query(Bill).filter_by(
                    payee=payee, 
                    is_active=True
                ).first()
                
                if not existing_bill:
                    suggestions.append(monthly_pattern)
    
    # Sort by confidence (highest first)
    suggestions.sort(key=lambda x: x.confidence, reverse=True)
    
    return suggestions

def create_bill_from_suggestion(suggestion: BillSuggestion) -> Bill:
    """Create a new Bill record from approved suggestion, linking supporting transactions as paid history"""
    new_bill = Bill(
        payee=suggestion.payee,
        expected_amount=suggestion.expected_amount,
        due_day=suggestion.due_day,
        frequency=suggestion.frequency,
        category_id=suggestion.category_id,
        is_active=True
    )

    session.add(new_bill)
    session.commit()

    # Link each supporting transaction as a historical paid instance
    for t in sorted(suggestion.supporting_transactions, key=lambda x: x.date):
        instance = BillInstance(
            bill_id=new_bill.id,
            due_date=t.date,
            actual_amount=abs(t.amount),
            status='paid',
            transaction_id=t.id
        )
        session.add(instance)

    session.commit()

    # Generate pending instances for the next 6 months
    generate_future_bill_instances(new_bill.id)

    return new_bill

def generate_future_bill_instances(bill_id: int, months: int = 6):
    """Generate future bill instances for a bill"""
    bill = session.query(Bill).get(bill_id)
    if not bill or bill.frequency != 'monthly':
        return
    
    today = date.today()
    
    for i in range(months):
        # Calculate due date for this month + i
        future_month = today + relativedelta(months=i)
        
        # Use the bill's due day, but handle month-end dates
        try:
            due_date = future_month.replace(day=bill.due_day)
        except ValueError:
            # Handle months that don't have the due day (e.g., day 31 in February)
            # Use last day of month instead
            next_month = future_month + relativedelta(months=1)
            due_date = (next_month.replace(day=1) - relativedelta(days=1))
        
        # Check if instance already exists
        existing_instance = session.query(BillInstance).filter_by(
            bill_id=bill_id,
            due_date=due_date
        ).first()
        
        if not existing_instance:
            instance = BillInstance(
                bill_id=bill_id,
                due_date=due_date,
                status='pending'
            )
            session.add(instance)
    
    session.commit()

def get_upcoming_bills(days: int = 30) -> List[BillInstance]:
    """Get bills due within specified number of days"""
    from datetime import timedelta
    
    end_date = date.today() + timedelta(days=days)
    
    upcoming = session.query(BillInstance).join(Bill).filter(
        BillInstance.due_date <= end_date,
        BillInstance.due_date >= date.today(),
        BillInstance.status == 'pending',
        Bill.is_active == True
    ).order_by(BillInstance.due_date).all()
    
    return upcoming

def get_overdue_bills() -> List[BillInstance]:
    """Get bills that are past due"""
    overdue = session.query(BillInstance).join(Bill).filter(
        BillInstance.due_date < date.today(),
        BillInstance.status == 'pending',
        Bill.is_active == True
    ).order_by(BillInstance.due_date).all()

    return overdue

def find_similar_transactions_for_bill(transaction_id: int) -> List[tuple]:
    """
    Find transactions similar to the given one, suitable for grouping into a recurring bill.

    Uses ML label similarity and amount proximity.
    Returns list of (Transaction, similarity_score) sorted by date (oldest first).
    The template transaction itself is NOT included in the results.
    """
    template = session.query(Transaction).get(transaction_id)
    if not template or template.amount >= 0:
        return []

    template_amount = abs(template.amount)

    # Get similarity scores for all labels in the index
    similar_label_pairs = find_similar_labels(template.label, threshold=0.5)
    label_score_map = {label: float(score) for label, score in similar_label_pairs}

    if not label_score_map:
        return []

    # Build set of transaction IDs already linked to a bill instance
    linked_ids: set = set(
        row[0] for row in session.query(BillInstance.transaction_id)
        .filter(BillInstance.transaction_id.isnot(None))
        .all()
    )

    # Query all debit transactions except the template
    candidates = session.query(Transaction).filter(
        Transaction.amount < 0,
        Transaction.id != transaction_id
    ).all()

    results = []
    for t in candidates:
        if t.id in linked_ids:
            continue

        score = label_score_map.get(t.label, 0.0)
        if score < 0.5:
            continue

        # Amount must be within ±25% of template
        if template_amount > 0:
            ratio = abs(t.amount) / template_amount
            if not (0.75 <= ratio <= 1.25):
                continue

        results.append((t, score))

    results.sort(key=lambda x: x[0].date)
    return results


def create_bill_with_transactions(
    payee: str,
    expected_amount: float,
    due_day: int,
    category_id: Optional[int],
    transactions: List[Transaction]
) -> Bill:
    """
    Create a new bill and attach the provided transactions as historical paid instances.
    Future pending instances are generated after linking the historical ones.
    """
    new_bill = Bill(
        payee=payee,
        expected_amount=expected_amount,
        due_day=due_day,
        frequency='monthly',
        category_id=category_id,
        is_active=True
    )
    session.add(new_bill)
    session.commit()

    for t in sorted(transactions, key=lambda x: x.date):
        instance = BillInstance(
            bill_id=new_bill.id,
            due_date=t.date,
            actual_amount=abs(t.amount),
            status='paid',
            transaction_id=t.id
        )
        session.add(instance)

    session.commit()
    generate_future_bill_instances(new_bill.id)
    return new_bill