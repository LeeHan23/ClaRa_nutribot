"""
Database Schema for NutriBot Patient Profiles
Defines the SQLAlchemy models and enums for patient data management.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Enum,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class ProfilingStatus(PyEnum):
    """Patient profiling status enumeration"""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class PatientProfile(Base):
    """
    Patient Profile Model
    
    Stores comprehensive patient health information for personalized
    nutrition advice and safety filtering.
    """
    __tablename__ = "patient_profiles"
    
    # Primary Identifier
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    
    # Basic Information
    name = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    
    # Medical Information (stored as comma-separated strings for simplicity)
    # In production, these could be separate tables with relationships
    medical_conditions = Column(Text, nullable=True)  # e.g., "CKD Stage 3, Diabetes Type 2"
    current_medications = Column(Text, nullable=True)  # e.g., "Warfarin, Lisinopril, Metformin"
    dietary_restrictions = Column(Text, nullable=True)  # e.g., "Vegetarian, Lactose intolerant"
    food_allergies = Column(Text, nullable=True)  # e.g., "Shellfish, Peanuts"
    
    # Profiling Status
    profiling_status = Column(
        Enum(ProfilingStatus),
        default=ProfilingStatus.NOT_STARTED,
        nullable=False
    )
    
    # Conversation Context (for maintaining state)
    last_question_asked = Column(String(500), nullable=True)
    conversation_history = Column(Text, nullable=True)  # JSON string of conversation
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    profiling_completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<PatientProfile(phone={self.phone_number}, name={self.name}, status={self.profiling_status})>"
    
    def is_profiling_complete(self) -> bool:
        """Check if all required fields are filled"""
        required_fields = [
            self.medical_conditions,
            self.current_medications,
            self.dietary_restrictions or self.food_allergies  # At least one should be answered
        ]
        return all(field is not None and field.strip() for field in required_fields[:-1])
    
    def get_missing_fields(self) -> list[str]:
        """Return list of missing required fields"""
        missing = []
        if not self.name:
            missing.append("name")
        if not self.medical_conditions:
            missing.append("medical_conditions")
        if not self.current_medications:
            missing.append("current_medications")
        if not self.dietary_restrictions and not self.food_allergies:
            missing.append("dietary_restrictions_or_allergies")
        return missing
    
    def to_context_string(self) -> str:
        """
        Convert patient profile to context string for CLaRa retriever
        This is crucial for medical safety filtering.
        """
        context_parts = []
        
        if self.name:
            context_parts.append(f"Patient: {self.name}")
        if self.age:
            context_parts.append(f"Age: {self.age}")
        if self.medical_conditions:
            context_parts.append(f"Medical Conditions: {self.medical_conditions}")
        if self.current_medications:
            context_parts.append(f"Current Medications: {self.current_medications}")
        if self.dietary_restrictions:
            context_parts.append(f"Dietary Restrictions: {self.dietary_restrictions}")
        if self.food_allergies:
            context_parts.append(f"Food Allergies: {self.food_allergies}")
        
        return "\n".join(context_parts)


# Database initialization
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/nutribot.db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at {DATABASE_URL}")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
