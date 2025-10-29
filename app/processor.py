# app/processor.py

import asyncio
from app.models import Transaction, TransactionStatus
from app.database import AsyncSessionLocal
import datetime

transaction_queue = asyncio.Queue()

async def process_transactions():
    while True:
        txn_id = await transaction_queue.get()
        async with AsyncSessionLocal() as session:
            txn = await session.get(Transaction, txn_id)
            if txn and txn.status == TransactionStatus.PROCESSING:
                await asyncio.sleep(30)  # Simulated delay
                txn.status = TransactionStatus.PROCESSED
                txn.processed_at = datetime.datetime.utcnow()
                await session.commit()
        transaction_queue.task_done()

async def enqueue_transaction(transactionid):
    await transaction_queue.put(transactionid)
