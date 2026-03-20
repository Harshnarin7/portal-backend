from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import random, string
from auth import hash_password, verify_password
from core.security import create_access_token
from models import Screening, BirthResuscitation, MaternalDetails, PostnatalDay1, NICUAdmission,NeonatalMorbidities,StudyOutcomes,CranialUltrasound,ROPScreening,CompositeOutcome,FiO2AUC,RespCVNeuroLog,InfectGIHemaLog,MetabRenalVascEyeLog,SAEReport, AdverseEvents, SAEList, User, get_db, Base, engine
from schemas import ScreeningCreate, ScreeningOut, BirthResuscitationCreate, BirthResuscitationOut, MaternalDetailsCreate, MaternalDetailsOut, PostnatalDay1Create, PostnatalDay1Out,NICUAdmissionCreate,NICUAdmissionOut,NeonatalMorbiditiesCreate,NeonatalMorbiditiesOut,StudyOutcomesCreate, StudyOutcomesOut,CranialUltrasoundCreate, CranialUltrasoundOut,ROPScreeningCreate, ROPScreeningOut,CompositeOutcomeCreate, CompositeOutcomeOut, FiO2AUCLogCreate, FiO2AUCLogOut, RespCVNeuroLogCreate, RespCVNeuroLogOut,InfectGIHemaLogCreate, InfectGIHemaLogOut,MetabRenalVascEyeLogCreate,MetabRenalVascEyeLogOut,SAEReportCreate, SAEReportOut, AdverseEventsCreate, AdverseEventsOut ,SAEListCreate, SAEListOut, UserCreate, UserOut, LoginRequest, LoginResponse
from pydantic import BaseModel
from typing import Optional, List
from deps import get_current_user
from routers import enrollment
from models import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE screenings ADD COLUMN consent_taken_by TEXT"))
        print("✅ consent_taken_by added")
    except Exception as e:
        print("⚠️ consent_taken_by exists:", e)

    try:
        conn.execute(text("ALTER TABLE screenings ADD COLUMN relationship_to_participant TEXT"))
        print("✅ relationship_to_participant added")
    except Exception as e:
        print("⚠️ relationship_to_participant exists:", e)

    try:
        conn.execute(text("ALTER TABLE screenings ADD COLUMN relationship_other TEXT"))
        print("✅ relationship_other added")
    except Exception as e:
        print("⚠️ relationship_other exists:", e)



# ----------------------------
# Database initialization
# ----------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PORTAL Trial API")
app.include_router(enrollment.router)

# ----------------------------
# Enable CORS for localhost:3000
# ----------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://portal-trial.netlify.app"
]
SITE_NURSES = {
    "PGIMER": [
        "Anureet Kaur",
        "Geetika",
        "Priyanka Thakur",
        "Seemran Kaur",
        "Tanvi Saini",
        "Yashvi Jolly",
        "Mannat Guliani",
        "Shalini Dhiman"
    ],
    "GMCH": [
        "Seemran Kaur",
        "Tanvi Saini"
    ],
    "IOG": [
        "Yashvi Jolly"
    ],
    "AFMC": [
        "Mannat Guliani",
        "Shalini Dhiman"
    ],
    "GMCH-A": [
        "Nurse A",
        "Nurse B"
    ],
    "AMC": [
        "Nurse A",
        "Nurse B"
    ]
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Helper functions: Auto-generate IDs
# ----------------------------
def generate_screening_id(site_id: str):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{site_id}-{timestamp}-{random_suffix}"


# ----------------------------
# ROOT endpoint
# ----------------------------
@app.get("/")
def root():
    return {"message": "PORTAL Trial API is running!"}
@app.get("/sites/{site_name}/screeners")
def get_site_screeners(site_name: str):
    nurses = SITE_NURSES.get(site_name)
    if not nurses:
        return []
    return nurses

# ----------------------------
# GET all screenings
# ----------------------------
@app.get("/screenings/", response_model=list[ScreeningOut])
def get_screenings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Screening).order_by(Screening.created_at.desc()).all()

# ----------------------------
# GET single screening by ID
# ----------------------------

def compute_screening_status(data):
    # 1. Gestation not determinable
    if data.gestation_weeks is None:
        return "Screen Failure"

    # 2. Gestation ≥ 32 weeks
    if data.gestation_weeks >= 32:
        return "Screen Failure"

    # 3. Any exclusion
    if data.exclusion_present:
        return "Screen Failure"

    # 4. Consent logic
    if data.consent_given == "Yes":
        return "Eligible"

    return "Not Eligible"

# ----------------------------
# CREATE a new screening
# ----------------------------
@app.post("/screenings/", response_model=ScreeningOut)
def create_screening(screening: ScreeningCreate, db: Session = Depends(get_db)):
    try:
        screening_id = generate_screening_id(screening.site_id)
        enrollment_id = screening.enrollment_id
        # ---------- Eligibility calculation ----------
        status = compute_screening_status(screening)


        db_screening = Screening(
    screening_id=screening_id,
    enrollment_id=enrollment_id,
    screening_datetime=screening.screening_datetime,
    created_at=datetime.now(),
    screening_status=status, 

    site_name=screening.site_name,
    site_id=screening.site_id,
    screened_by=screening.screened_by,

    mother_first_name=screening.mother_first_name,
    mother_surname=screening.mother_surname,
    husband_first_name=screening.husband_first_name,
    husband_surname=screening.husband_surname,

    maternal_uid=screening.maternal_uid,
    hospital_admission_number=screening.hospital_admission_number,

    gestation_weeks=screening.gestation_weeks,
    gestation_days=screening.gestation_days,
    gestation_method=screening.gestation_method,
    expected_delivery_date=screening.expected_delivery_date,

    exclusion_present=screening.exclusion_present,
    exclusion_reasons=screening.exclusion_reasons,

    consent_given=screening.consent_given,
    consent_taken_by=screening.consent_taken_by,
    relationship_to_participant=screening.relationship_to_participant,
    relationship_other=screening.relationship_other,
    reason_not_approached=screening.reason_not_approached,
)
        db.add(db_screening)
        db.commit()
        db.refresh(db_screening)
        return db_screening

    except Exception as e:
        print("🔥 SCREENING ERROR:", e)
        
        raise HTTPException(status_code=400, detail=f"Unexpected error: {str(e)}")
    
@app.get("/screenings/{screening_id}", response_model=ScreeningOut)
def get_screening(screening_id: str, db: Session = Depends(get_db)):
    entry = db.query(Screening).filter(
        Screening.screening_id == screening_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Screening not found")

    return entry    

# ----------------------------
# UPDATE screening
# ----------------------------
@app.put("/screenings/{id}", response_model=ScreeningOut)
def update_screening(id: int, updated_data: ScreeningCreate, db: Session = Depends(get_db)):
    entry = db.query(Screening).filter(Screening.id == id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Screening entry not found")

    try:
        for key, value in updated_data.model_dump().items():
            setattr(entry, key, value)

        db.commit()
        db.refresh(entry)
        return entry

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating entry: {str(e)}")

# ----------------------------
# DELETE screening
# ----------------------------
@app.delete("/screenings/{id}")
def delete_screening(id: int, db: Session = Depends(get_db)):
    entry = db.query(Screening).filter(Screening.id == id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Screening entry not found")

    try:
        db.delete(entry)
        db.commit()
        return {"message": f"Entry with ID {id} deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting entry: {str(e)}")

@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_pwd = hash_password(user.password)

    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pwd,
        role=user.role,
        site_name=user.site_name
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user





@app.post("/auth/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "site_name": user.site_name,
    })

    return {
        "access_token": token,
        "role": user.role,
        "site_name": user.site_name,
    }
# ==========================================================
# 🧾 FORM B — BIRTH RESUSCITATION ROUTES
# ==========================================================

@app.post("/birth-resuscitation/")
def create_birth_resuscitation(
    data: BirthResuscitationCreate,
    db: Session = Depends(get_db)
):
    print("📦 Received Birth Resuscitation data:", data.model_dump())

    entry = BirthResuscitation(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return entry
@app.get("/birth-resuscitation/{enrollment_id}", response_model=BirthResuscitationOut)
def get_birth_resuscitation(enrollment_id: str, db: Session = Depends(get_db)):
    entry = (
        db.query(BirthResuscitation)
        .filter(BirthResuscitation.enrollment_id == enrollment_id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Birth Resuscitation not found")

    return entry    

@app.post("/maternal-details/", response_model=MaternalDetailsOut)
def create_maternal_details(
    data: MaternalDetailsCreate,
    db: Session = Depends(get_db),
):
    record = MaternalDetails(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ==========================================================
# 🧾 FORM D — POSTNATAL DAY 1 ROUTES
# ==========================================================

@app.post("/postnatal-day1/", response_model=PostnatalDay1Out)
def create_postnatal_day1(
    data: PostnatalDay1Create,
    db: Session = Depends(get_db),
):
    record = PostnatalDay1(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
@app.get("/postnatal-day1/{enrollment_id}")
def get_postnatal_day1(enrollment_id: str, db: Session = Depends(get_db)):
    record = db.query(PostnatalDay1).filter(
        PostnatalDay1.enrollment_id == enrollment_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Form D not found")

    return record    

# ==========================================================
# 🏥 FORM E — NICU ADMISSION ROUTES
# ==========================================================

@app.post("/nicu-admission/", response_model=NICUAdmissionOut)
def create_nicu_admission(
    data: NICUAdmissionCreate,
    db: Session = Depends(get_db)
):
    record = NICUAdmission(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/nicu-admission/{enrollment_id}", response_model=list[NICUAdmissionOut])
def get_nicu_admission(enrollment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(NICUAdmission)
        .filter(NICUAdmission.enrollment_id == enrollment_id)
        .all()
    )
# ==========================================================
# FORM F — NEONATAL MORBIDITIES API
# ==========================================================

@app.post("/neonatal-morbidities/", response_model=NeonatalMorbiditiesOut)
def create_neonatal_morbidities(
    data: NeonatalMorbiditiesCreate,
    db: Session = Depends(get_db),
):
    record = NeonatalMorbidities(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/neonatal-morbidities/{enrollment_id}", response_model=list[NeonatalMorbiditiesOut])
def get_neonatal_morbidities(
    enrollment_id: str,
    db: Session = Depends(get_db),
):
    return (
        db.query(NeonatalMorbidities)
        .filter(NeonatalMorbidities.enrollment_id == enrollment_id)
        .all()
    )


# ==========================================================
# FORM G — STUDY OUTCOMES ROUTES
# ==========================================================

@app.post("/study-outcomes/", response_model=StudyOutcomesOut)
def create_study_outcomes(
    data: StudyOutcomesCreate,
    db: Session = Depends(get_db)
):
    record = StudyOutcomes(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.post("/cranial-ultrasound/", response_model=CranialUltrasoundOut)
def create_cranial_ultrasound(
    data: CranialUltrasoundCreate,
    db: Session = Depends(get_db)
):
    record = CranialUltrasound(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.post("/rop-screening/", response_model=ROPScreeningOut)
def create_rop_screening(
    data: ROPScreeningCreate,
    db: Session = Depends(get_db)
):
    record = ROPScreening(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ==========================================================
# FORM J — COMPOSITE OUTCOME ROUTES
# ==========================================================

@app.post("/composite-outcome/", response_model=CompositeOutcomeOut)
def create_composite_outcome(
    data: CompositeOutcomeCreate,
    db: Session = Depends(get_db)
):
    record = CompositeOutcome(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/composite-outcome/{enrollment_id}", response_model=list[CompositeOutcomeOut])
def get_composite_outcome(
    enrollment_id: str,
    db: Session = Depends(get_db)
):
    return (
        db.query(CompositeOutcome)
        .filter(CompositeOutcome.enrollment_id == enrollment_id)
        .order_by(CompositeOutcome.created_at.desc())
        .all()
    )


@app.post("/fio2-auc/", response_model=FiO2AUCLogOut)
def create_fio2_auc(
    data: FiO2AUCLogCreate,
    db: Session = Depends(get_db)
):
    record = FiO2AUC(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/fio2-auc/{enrollment_id}", response_model=list[FiO2AUCLogOut])
def get_fio2_auc(
    enrollment_id: str,
    db: Session = Depends(get_db)
):
    return (
        db.query(FiO2AUC)
        .filter(FiO2AUC.enrollment_id == enrollment_id)
        .order_by(FiO2AUC.created_at.desc())
        .all()
    )



# ==========================================================
# HELPER FORM VS6.1 — RESP / CV / NEURO ROUTES
# ==========================================================

@app.post("/resp-cv-neuro-log/", response_model=RespCVNeuroLogOut)
def create_resp_cv_neuro_log(
    data: RespCVNeuroLogCreate,
    db: Session = Depends(get_db)
):
    record = RespCVNeuroLog(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/resp-cv-neuro-log/{enrollment_id}", response_model=list[RespCVNeuroLogOut])
def get_resp_cv_neuro_log(
    enrollment_id: str,
    db: Session = Depends(get_db)
):
    return (
        db.query(RespCVNeuroLog)
        .filter(RespCVNeuroLog.enrollment_id == enrollment_id)
        .order_by(RespCVNeuroLog.created_at.desc())
        .all()
    )



@app.post("/infect-gi-hema-log/", response_model=InfectGIHemaLogOut)
def create_infect_gi_hema_log(
    data: InfectGIHemaLogCreate,
    db: Session = Depends(get_db)
):
    record = InfectGIHemaLog(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.post(
    "/metab-renal-vasc-eye-log/",
    response_model=MetabRenalVascEyeLogOut
)
def create_metab_renal_vasc_eye_log(
    data: MetabRenalVascEyeLogCreate,
    db: Session = Depends(get_db)
):
    record = MetabRenalVascEyeLog(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record



@app.post("/sae-report/", response_model=SAEReportOut)
def create_sae_report(
    data: SAEReportCreate,
    db: Session = Depends(get_db)
):
    record = SAEReport(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.post("/adverse-events/", response_model=AdverseEventsOut)
def create_adverse_events(
    data: AdverseEventsCreate,
    db: Session = Depends(get_db)
):
    record = AdverseEvents(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.post("/sae-list/", response_model=SAEListOut)
def create_sae_list(
    data: SAEListCreate,
    db: Session = Depends(get_db)
):
    record = SAEList(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.get("/postnatal-day1/{enrollment_id}")
def get_postnatal_day1(enrollment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(PostnatalDay1)
        .filter(PostnatalDay1.enrollment_id == enrollment_id)
        .first()
    )

@app.get("/maternal-details/{enrollment_id}")
def get_maternal_details(enrollment_id: str, db: Session = Depends(get_db)):
    return (
        db.query(MaternalDetails)
        .filter(MaternalDetails.enrollment_id == enrollment_id)
        .first()
    )


@app.get("/enrollment-status/{enrollment_id}")
def get_enrollment_status(
    enrollment_id: str,
    db: Session = Depends(get_db),
):
    screening = (
        db.query(Screening)
        .filter(Screening.enrollment_id == enrollment_id)
        .first()
    )

    if not screening:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    form_b = (
        db.query(BirthResuscitation)
        .filter(BirthResuscitation.enrollment_id == enrollment_id)
        .first()
        is not None
    )

    form_c = (
        db.query(MaternalDetails)
        .filter(MaternalDetails.enrollment_id == enrollment_id)
        .first()
        is not None
    )

    form_d = (
        db.query(PostnatalDay1)
        .filter(PostnatalDay1.enrollment_id == enrollment_id)
        .first()
        is not None
    )

    # decide next form
    if not form_b:
        next_form = "form-b"
    elif not form_c:
        next_form = "form-c"
    elif not form_d:
        next_form = "form-d"
    else:
        next_form = "completed"

    return {
        "enrollment_id": enrollment_id,
        "screening_status": screening.screening_status,
        "form_a": True,
        "form_b": form_b,
        "form_c": form_c,
        "form_d": form_d,
        "next_form": next_form,
    }
@app.get("/screenings/by-screening-id/{screening_id}", response_model=ScreeningOut)
def get_screening_by_screening_id(screening_id: str, db: Session = Depends(get_db)):
    entry = db.query(Screening).filter(
        Screening.screening_id == screening_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Screening not found")

    return entry

@app.get("/screenings/by-enrollment/{enrollment_id}", response_model=ScreeningOut)
def get_screening_by_enrollment(enrollment_id: str, db: Session = Depends(get_db)):
    entry = db.query(Screening).filter(
        Screening.enrollment_id == enrollment_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Screening not found")

    return entry    