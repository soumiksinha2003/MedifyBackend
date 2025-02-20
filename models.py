from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Caregiver(Base):
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    individuals = relationship("Individual", back_populates="caregiver")

class Individual(Base):
    __tablename__ = "individuals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))

    caregiver = relationship("Caregiver", back_populates="individuals")
    medications = relationship("Medication", back_populates="individual")

class Medication(Base):
    __tablename__ = "medications"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    time = Column(String, nullable=False)
    days_remaining = Column(Integer, nullable=False)
    taken = Column(Boolean, default=False)
    individual_id = Column(Integer, ForeignKey("individuals.id"))

    individual = relationship("Individual", back_populates="medications")
