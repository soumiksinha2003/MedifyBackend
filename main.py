from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Caregiver, Individual, Medication
from schemas import CaregiverCreate, IndividualCreate, MedicationCreate, MedicationUpdate, AdherenceUpdate
from security import get_password_hash, verify_password, create_access_token
from dependencies import get_db
from fastapi.security import OAuth2PasswordRequestForm
from twilio.rest import Client
import os
import time
from datetime import datetime, timedelta
import threading

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Twilio Config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.get("/")
def read_root():
    return {"message": "Welcome to MedifyBackend"}


# Register Caregiver
@app.post("/register")
def register_caregiver(caregiver: CaregiverCreate, db: Session = Depends(get_db)):
    db_caregiver = db.query(Caregiver).filter(Caregiver.email == caregiver.email).first()
    if db_caregiver:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(caregiver.password)
    new_caregiver = Caregiver(
        name=caregiver.name, 
        email=caregiver.email, 
        password=hashed_password,
        phone=caregiver.phone  # ✅ Fix: Store phone
    )
    print(new_caregiver.phone)
    db.add(new_caregiver)
    db.commit()
    db.refresh(new_caregiver)
    return {"message": "User registered successfully"}

# Login
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    caregiver = db.query(Caregiver).filter(Caregiver.email == form_data.username).first()
    if not caregiver or not verify_password(form_data.password, caregiver.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": caregiver.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Add Individual
@app.post("/individuals")
def add_individual(individual: IndividualCreate, db: Session = Depends(get_db)):
    new_individual = Individual(name=individual.name, caregiver_id=individual.caregiver_id)
    db.add(new_individual)
    db.commit()
    db.refresh(new_individual)
    return new_individual

# Add Medication
@app.post("/medications")
def add_medication(medication: MedicationCreate, db: Session = Depends(get_db)):
    new_medication = Medication(name=medication.name, time=medication.time, days_remaining=medication.days_remaining, individual_id=medication.individual_id)
    db.add(new_medication)
    db.commit()
    db.refresh(new_medication)
    return new_medication

# Update Medication
@app.put("/medications/{med_id}")
def update_medication(med_id: int, med_update: MedicationUpdate, db: Session = Depends(get_db)):
    medication = db.query(Medication).filter(Medication.id == med_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    medication.time = med_update.time
    medication.days_remaining = med_update.days_remaining
    db.commit()
    return {"message": "Medication updated successfully"}

# Mark Medication as Taken
@app.put("/medications/{med_id}/adherence")
def mark_adherence(med_id: int, adherence_update: AdherenceUpdate, db: Session = Depends(get_db)):
    medication = db.query(Medication).filter(Medication.id == med_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    medication.taken = adherence_update.taken
    if adherence_update.taken:
        medication.days_remaining -= 1
    db.commit()
    return {"message": "Adherence updated successfully"}

# Twilio Call Reminder with Retry Logic
@app.post("/reminder/{med_id}")
def send_reminder(med_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    medication = db.query(Medication).filter(Medication.id == med_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    individual = medication.individual
    caregiver = individual.caregiver
    print(caregiver.phone,"this is printing")
    if not caregiver.phone:  # ✅ Fix: Ensure phone exists
        raise HTTPException(status_code=400, detail="Caregiver phone number is missing")
    
    def retry_call():
        time.sleep(300)  # Wait 5 minutes
        if not medication.taken:
            client.calls.create(
                twiml=f"<Response><Say>You missed your {medication.name} dose. Please take it as soon as possible.</Say></Response>",
                to=caregiver.phone,
                from_=TWILIO_PHONE_NUMBER
            )
            missed_count = db.query(Medication).filter(Medication.id == med_id, Medication.taken == False).count()
            if missed_count >= 3:
                client.messages.create(
                    body=f"Alert: {individual.name} has missed {missed_count} doses of {medication.name}.",
                    from_=TWILIO_PHONE_NUMBER,
                    to=caregiver.phone
                )

    call = client.calls.create(
        twiml=f"<Response><Say>It's time to take your {medication.name} medication. Please confirm by pressing 1.</Say></Response>",
        to=caregiver.phone,
        from_=TWILIO_PHONE_NUMBER
    )
    background_tasks.add_task(retry_call)
    return {"message": "Call reminder sent", "call_sid": call.sid}

