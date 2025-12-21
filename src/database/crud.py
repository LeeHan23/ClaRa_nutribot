"""
CRUD Operations for Patient Profiles
Provides database operations for patient management.
"""

from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from .schema import PatientProfile, ProfilingStatus


class PatientCRUD:
    """Patient Profile CRUD operations"""
    
    @staticmethod
    def get_or_create_patient(db: Session, phone_number: str) -> PatientProfile:
        """
        Get existing patient or create new one
        
        Args:
            db: Database session
            phone_number: Patient's WhatsApp phone number
            
        Returns:
            PatientProfile: Existing or newly created patient
        """
        patient = db.query(PatientProfile).filter(
            PatientProfile.phone_number == phone_number
        ).first()
        
        if not patient:
            patient = PatientProfile(
                phone_number=phone_number,
                profiling_status=ProfilingStatus.NOT_STARTED
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            print(f"✅ Created new patient profile for {phone_number}")
        
        return patient
    
    @staticmethod
    def update_patient_field(
        db: Session,
        phone_number: str,
        field_name: str,
        value: any
    ) -> PatientProfile:
        """
        Update a specific field for a patient
        
        Args:
            db: Database session
            phone_number: Patient identifier
            field_name: Name of field to update
            value: New value
            
        Returns:
            Updated PatientProfile
        """
        patient = PatientCRUD.get_or_create_patient(db, phone_number)
        setattr(patient, field_name, value)
        patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patient)
        return patient
    
    @staticmethod
    def update_profiling_status(
        db: Session,
        phone_number: str,
        status: ProfilingStatus
    ) -> PatientProfile:
        """
        Update patient profiling status
        
        Args:
            db: Database session
            phone_number: Patient identifier
            status: New ProfilingStatus
            
        Returns:
            Updated PatientProfile
        """
        patient = PatientCRUD.get_or_create_patient(db, phone_number)
        patient.profiling_status = status
        
        if status == ProfilingStatus.COMPLETE:
            patient.profiling_completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(patient)
        return patient
    
    @staticmethod
    def save_patient_info(
        db: Session,
        phone_number: str,
        name: Optional[str] = None,
        age: Optional[int] = None,
        medical_conditions: Optional[str] = None,
        current_medications: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        food_allergies: Optional[str] = None
    ) -> PatientProfile:
        """
        Save multiple patient information fields at once
        
        Args:
            db: Database session
            phone_number: Patient identifier
            **kwargs: Fields to update
            
        Returns:
            Updated PatientProfile
        """
        patient = PatientCRUD.get_or_create_patient(db, phone_number)
        
        if name is not None:
            patient.name = name
        if age is not None:
            patient.age = age
        if medical_conditions is not None:
            patient.medical_conditions = medical_conditions
        if current_medications is not None:
            patient.current_medications = current_medications
        if dietary_restrictions is not None:
            patient.dietary_restrictions = dietary_restrictions
        if food_allergies is not None:
            patient.food_allergies = food_allergies
        
        # Auto-update profiling status based on completeness
        if patient.is_profiling_complete():
            patient.profiling_status = ProfilingStatus.COMPLETE
            if not patient.profiling_completed_at:
                patient.profiling_completed_at = datetime.utcnow()
        elif patient.profiling_status == ProfilingStatus.NOT_STARTED:
            patient.profiling_status = ProfilingStatus.IN_PROGRESS
        
        patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patient)
        return patient
    
    @staticmethod
    def get_patient_by_phone(
        db: Session,
        phone_number: str
    ) -> Optional[PatientProfile]:
        """
        Retrieve patient by phone number
        
        Args:
            db: Database session
            phone_number: Patient identifier
            
        Returns:
            PatientProfile or None
        """
        return db.query(PatientProfile).filter(
            PatientProfile.phone_number == phone_number
        ).first()
    
    @staticmethod
    def delete_patient(db: Session, phone_number: str) -> bool:
        """
        Delete patient profile (for testing/GDPR compliance)
        
        Args:
            db: Database session
            phone_number: Patient identifier
            
        Returns:
            True if deleted, False if not found
        """
        patient = PatientCRUD.get_patient_by_phone(db, phone_number)
        if patient:
            db.delete(patient)
            db.commit()
            return True
        return False
