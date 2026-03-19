from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Screening
from deps import get_db

router = APIRouter(prefix="/screenings", tags=["Screenings"])


@router.get("/{screening_id}")
def get_screening(screening_id: str, db: Session = Depends(get_db)):
    screening = db.query(Screening).filter(
        Screening.screening_id == screening_id
    ).first()

    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")

    return screening