from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import (
    Screening,
    BirthResuscitation,
    MaternalDetails,
    PostnatalDay1
)
from deps import get_db

router = APIRouter(prefix="/enrollment", tags=["Enrollment Progress"])


@router.get("/status/{enrollment_id}")
def get_enrollment_status(enrollment_id: str, db: Session = Depends(get_db)):
    screening = db.query(Screening).filter(
        Screening.enrollment_id == enrollment_id
    ).first()

    if not screening:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    form_b = db.query(BirthResuscitation).filter(
        BirthResuscitation.enrollment_id == enrollment_id
    ).first()

    form_c = db.query(MaternalDetails).filter(
        MaternalDetails.enrollment_id == enrollment_id
    ).first()

    form_d = db.query(PostnatalDay1).filter(
        PostnatalDay1.enrollment_id == enrollment_id
    ).first()

    return {
        "enrollment_id": enrollment_id,
        "formA": True,
        "formB": form_b is not None,
        "formC": form_c is not None,
        "formD": form_d is not None,
    }
@router.get("/screenings/{screening_id}")
def get_screening(screening_id: str, db: Session = Depends(get_db)):
    screening = db.query(Screening).filter(
        Screening.screening_id == screening_id
    ).first()

    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")

    return screening