# app/main.py

from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
import datetime
from app.database import AsyncSessionLocal, init_db
from app.models import Transaction, TransactionStatus
from app.processor import enqueue_transaction, process_transactions
import asyncio

app = FastAPI()

# Startup event to launch processor
@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(process_transactions())

@app.get("/")
async def health():
    return {"status": "HEALTHY", "current_time": datetime.datetime.utcnow().isoformat()}

@app.post("/v1/webhooks/transactions", status_code=status.HTTP_202_ACCEPTED)
async def webhook(request: Request):
    data = await request.json()
    async with AsyncSessionLocal() as session:
        txn = await session.get(Transaction, data["transaction_id"])
        if txn:
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"message": "Already processing"})
        txn = Transaction(
            transaction_id=data["transaction_id"],
            source_account=data["source_account"],
            destination_account=data["destination_account"],
            amount=data["amount"],
            currency=data["currency"],
            status=TransactionStatus.PROCESSING,
            created_at=datetime.datetime.utcnow()
        )
        session.add(txn)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"message": "Idempotent: already exists"})
        await enqueue_transaction(data["transaction_id"])
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"message": "Queued for processing"})

@app.get("/v1/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    async with AsyncSessionLocal() as session:
        txn = await session.get(Transaction, transaction_id)
        if not txn:
            return JSONResponse(status_code=404, content={"error": "Transaction not found"})
        return {
            "transaction_id": txn.transaction_id,
            "source_account": txn.source_account,
            "destination_account": txn.destination_account,
            "amount": txn.amount,
            "currency": txn.currency,
            "status": txn.status.value,
            "created_at": txn.created_at.isoformat(),
            "processed_at": txn.processed_at.isoformat() if txn.processed_at else None
        }
