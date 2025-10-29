

import enum
from sqlalchemy import Column, String, Float, Index, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime
from sqlalchemy import Enum
Base = declarative_base()


class TransactionStatus(enum.Enum):
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    
class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(String, primary_key=True, index=True)
    source_account = Column(String, nullable=False)
    destination_account = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PROCESSING, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
