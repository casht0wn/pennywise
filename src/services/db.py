import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

Base = declarative_base()
engine = create_engine('sqlite:///storage/data/pennywise.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    label = Column(String, nullable=False)
    normalized_label = Column(String, nullable=True) # Allow null values
    payee = Column(String, nullable=True)  # Allow null values
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)  # Allow null values
    debit = Column(Float, nullable=False, default=0.0)
    credit = Column(Float, nullable=False, default=0.0)
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Transaction(date={self.date}, label={self.label}, amount={self.amount})>"
    
class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<Category(name={self.name})>"

class Bill(Base):
    __tablename__ = 'bills'
    id = Column(Integer, primary_key=True, index=True)
    payee = Column(String, nullable=False)
    expected_amount = Column(Float, nullable=False)
    due_day = Column(Integer, nullable=False)  # Day of month (1-31)
    frequency = Column(String, nullable=False, default='monthly')  # monthly, weekly, etc.
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    category = relationship("Category")
    bill_instances = relationship("BillInstance", back_populates="bill")

    def __repr__(self):
        return f"<Bill(payee={self.payee}, amount={self.expected_amount}, due_day={self.due_day})>"

class BillInstance(Base):
    __tablename__ = 'bill_instances'
    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey('bills.id'), nullable=False)
    due_date = Column(Date, nullable=False)
    actual_amount = Column(Float, nullable=True)
    status = Column(String, nullable=False, default='pending')  # pending, paid, overdue
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    
    # Relationships  
    bill = relationship("Bill", back_populates="bill_instances")
    transaction = relationship("Transaction")

    def __repr__(self):
        return f"<BillInstance(bill_id={self.bill_id}, due_date={self.due_date}, status={self.status})>"

Base.metadata.create_all(bind=engine)