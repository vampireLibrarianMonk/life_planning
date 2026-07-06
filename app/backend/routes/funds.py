"""Fund tracking routes — drawdown ledgers for earmarked money (e.g., insurance fund)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin_or_child
from database import get_db
from models import Fund, FundTransaction, User

router = APIRouter(prefix="/api/profiles/{profile_id}/funds", tags=["funds"])


class FundCreate(BaseModel):
    name: str
    description: str | None = None
    starting_balance: int  # cents


class FundUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TransactionCreate(BaseModel):
    amount: int  # cents (positive = money out)
    description: str
    date: str | None = None  # YYYY-MM-DD


class FundResponse(BaseModel):
    id: int
    profile_id: int
    name: str
    description: str | None
    starting_balance: int
    current_balance: int
    total_disbursed: int
    transaction_count: int
    created_at: str | None

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    id: int
    fund_id: int
    amount: int
    description: str
    date: str | None
    balance_after: int
    created_at: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[FundResponse])
def list_funds(profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """List all funds for a profile with current balances."""
    funds = db.query(Fund).filter(Fund.profile_id == profile_id).all()
    results = []
    for f in funds:
        total_disbursed = sum(t.amount for t in f.transactions)
        results.append({
            "id": f.id,
            "profile_id": f.profile_id,
            "name": f.name,
            "description": f.description,
            "starting_balance": f.starting_balance,
            "current_balance": f.starting_balance - total_disbursed,
            "total_disbursed": total_disbursed,
            "transaction_count": len(f.transactions),
            "created_at": str(f.created_at) if f.created_at else None,
        })
    return results


@router.post("/", response_model=FundResponse, status_code=201)
def create_fund(profile_id: int, req: FundCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Create a new fund (e.g., Earn Your Car Insurance Fund)."""
    fund = Fund(profile_id=profile_id, **req.model_dump())
    db.add(fund)
    db.commit()
    db.refresh(fund)
    return {
        "id": fund.id,
        "profile_id": fund.profile_id,
        "name": fund.name,
        "description": fund.description,
        "starting_balance": fund.starting_balance,
        "current_balance": fund.starting_balance,
        "total_disbursed": 0,
        "transaction_count": 0,
        "created_at": str(fund.created_at) if fund.created_at else None,
    }


@router.delete("/{fund_id}", status_code=204)
def delete_fund(profile_id: int, fund_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Delete a fund and all its transactions."""
    fund = db.query(Fund).filter(Fund.id == fund_id, Fund.profile_id == profile_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    db.delete(fund)
    db.commit()


@router.get("/{fund_id}/transactions", response_model=list[TransactionResponse])
def list_transactions(profile_id: int, fund_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """List all transactions for a fund with running balance."""
    fund = db.query(Fund).filter(Fund.id == fund_id, Fund.profile_id == profile_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    transactions = db.query(FundTransaction).filter(FundTransaction.fund_id == fund_id).order_by(FundTransaction.created_at).all()
    results = []
    running = fund.starting_balance
    for t in transactions:
        running -= t.amount
        results.append({
            "id": t.id,
            "fund_id": t.fund_id,
            "amount": t.amount,
            "description": t.description,
            "date": t.date,
            "balance_after": running,
            "created_at": str(t.created_at) if t.created_at else None,
        })
    return results


@router.post("/{fund_id}/transactions", response_model=TransactionResponse, status_code=201)
def create_transaction(profile_id: int, fund_id: int, req: TransactionCreate, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Record a disbursement from the fund."""
    fund = db.query(Fund).filter(Fund.id == fund_id, Fund.profile_id == profile_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    # Calculate current balance
    total_disbursed = sum(t.amount for t in fund.transactions)
    current_balance = fund.starting_balance - total_disbursed
    if req.amount > current_balance:
        raise HTTPException(status_code=400, detail=f"Insufficient fund balance. Available: ${current_balance / 100:.2f}")
    txn = FundTransaction(fund_id=fund_id, **req.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return {
        "id": txn.id,
        "fund_id": txn.fund_id,
        "amount": txn.amount,
        "description": txn.description,
        "date": txn.date,
        "balance_after": current_balance - txn.amount,
        "created_at": str(txn.created_at) if txn.created_at else None,
    }


@router.delete("/{fund_id}/transactions/{txn_id}", status_code=204)
def delete_transaction(profile_id: int, fund_id: int, txn_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_or_child)):
    """Delete a transaction (reverses the disbursement)."""
    txn = db.query(FundTransaction).filter(FundTransaction.id == txn_id, FundTransaction.fund_id == fund_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
