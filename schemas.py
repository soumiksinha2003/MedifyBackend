from pydantic import BaseModel

class CaregiverCreate(BaseModel):
    name: str
    email: str
    password: str
    phone: str  # ✅ Fix: Include phone

class IndividualCreate(BaseModel):
    name: str
    caregiver_id: int

class MedicationCreate(BaseModel):
    name: str
    time: str
    days_remaining: int
    individual_id: int

class MedicationUpdate(BaseModel):
    time: str
    days_remaining: int

class AdherenceUpdate(BaseModel):
    taken: bool
