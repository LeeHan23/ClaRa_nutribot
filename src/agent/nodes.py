"""
LangGraph Agent Nodes

Implements the Intake Nurse and Clinical Dietitian nodes
for the agentic state machine.
"""

import os
from typing import Dict, Any
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from src.database.schema import SessionLocal, ProfilingStatus
from src.database.crud import PatientCRUD
from src.agent.prompts import (
    INTAKE_NURSE_PROMPT,
    DIETITIAN_PROMPT,
    PROFILING_QUESTIONS,
    PROFILING_COMPLETE_MESSAGE,
    ERROR_MESSAGES
)
from src.retriever.clara_engine import ClaraRetriever

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
    temperature=0.7
)


class IntakeNurseNode:
    """
    Intake Nurse - Conducts patient interview to gather health profile
    
    Responsibilities:
    1. Check database for patient profile completeness
    2. Identify missing required fields
    3. Generate empathetic interview question
    4. Store user responses in database
    5. Update profiling status
    """
    
    @staticmethod
    def process(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user message in Nurse mode
        
        Args:
            state: Current conversation state containing:
                - phone_number: User identifier
                - user_message: Latest user input
                - conversation_history: Previous messages
        
        Returns:
            Updated state with agent_response
        """
        phone_number = state["phone_number"]
        user_message = state["user_message"]
        
        logger.info(f"👩‍⚕️ Nurse Node processing for {phone_number}")
        
        db = SessionLocal()
        try:
            # Get or create patient profile
            patient = PatientCRUD.get_or_create_patient(db, phone_number)
            
            # Determine next question based on missing fields
            missing_fields = patient.get_missing_fields()
            
            if not missing_fields:
                # Profile is complete - transition to Dietitian
                logger.success(f"✅ Profiling complete for {phone_number}")
                patient = PatientCRUD.update_profiling_status(
                    db, phone_number, ProfilingStatus.COMPLETE
                )
                
                state["agent_response"] = PROFILING_COMPLETE_MESSAGE
                state["next_mode"] = "dietitian"
                return state
            
            # Update profiling status to IN_PROGRESS if not started
            if patient.profiling_status == ProfilingStatus.NOT_STARTED:
                PatientCRUD.update_profiling_status(
                    db, phone_number, ProfilingStatus.IN_PROGRESS
                )
            
            # Extract information from user message using LLM
            if user_message and user_message.lower() not in ["hi", "hello", "hey", "start"]:
                # User provided information - extract and store
                extracted_info = IntakeNurseNode._extract_patient_info(
                    user_message,
                    patient.last_question_asked,
                    missing_fields[0] if missing_fields else None
                )
                
                # Update patient profile
                if extracted_info:
                    PatientCRUD.save_patient_info(db, phone_number, **extracted_info)
                    logger.info(f"📝 Updated patient info: {extracted_info}")
                    
                    # Refresh patient data
                    patient = PatientCRUD.get_patient_by_phone(db, phone_number)
                    missing_fields = patient.get_missing_fields()
            
            # Check again if profile is now complete
            if not missing_fields:
                patient = PatientCRUD.update_profiling_status(
                    db, phone_number, ProfilingStatus.COMPLETE
                )
                state["agent_response"] = PROFILING_COMPLETE_MESSAGE
                state["next_mode"] = "dietitian"
                return state
            
            # Generate next question
            next_field = missing_fields[0]
            next_question = IntakeNurseNode._generate_next_question(
                next_field, patient
            )
            
            # Store question in database
            PatientCRUD.update_patient_field(
                db, phone_number, "last_question_asked", next_question
            )
            
            state["agent_response"] = next_question
            state["next_mode"] = "nurse"
            return state
            
        finally:
            db.close()
    
    @staticmethod
    def _extract_patient_info(
        user_message: str,
        last_question: str,
        expected_field: str
    ) -> Dict[str, Any]:
        """
        Use LLM to extract structured information from user response
        
        Args:
            user_message: User's text input
            last_question: Question that was asked
            expected_field: Field we're trying to fill
        
        Returns:
            Dict with extracted field values
        """
        extraction_prompt = f"""You are extracting patient health information from a conversational response.

Last Question Asked: "{last_question}"
Expected Field: {expected_field}
User Response: "{user_message}"

Extract and return ONLY the relevant information in this exact format:

If extracting NAME:
{{"name": "extracted name"}}

If extracting MEDICAL_CONDITIONS:
{{"medical_conditions": "comma-separated conditions"}}

If extracting CURRENT_MEDICATIONS:
{{"current_medications": "comma-separated medications"}}

If extracting DIETARY_RESTRICTIONS:
{{"dietary_restrictions": "restrictions or None if none mentioned"}}

If extracting FOOD_ALLERGIES:
{{"food_allergies": "allergies or None if none mentioned"}}

If user says "none" or "no" for medications/allergies/restrictions, use "None".

Return ONLY valid JSON, nothing else."""
        
        try:
            response = llm.invoke([HumanMessage(content=extraction_prompt)])
            # Parse JSON from response
            import json
            extracted = json.loads(response.content.strip())
            return extracted
        except Exception as e:
            logger.error(f"❌ Info extraction failed: {e}")
            # Fallback: simple keyword matching
            return IntakeNurseNode._fallback_extraction(
                user_message, expected_field
            )
    
    @staticmethod
    def _fallback_extraction(user_message: str, expected_field: str) -> Dict[str, Any]:
        """Fallback extraction using simple rules"""
        result = {}
        
        if "none" in user_message.lower() or "no" in user_message.lower():
            value = "None"
        else:
            value = user_message.strip()
        
        if expected_field == "name":
            result["name"] = value
        elif expected_field == "medical_conditions":
            result["medical_conditions"] = value
        elif expected_field == "current_medications":
            result["current_medications"] = value
        elif expected_field == "dietary_restrictions":
            result["dietary_restrictions"] = value
        elif expected_field == "food_allergies":
            result["food_allergies"] = value
        
        return result
    
    @staticmethod
    def _generate_next_question(field_name: str, patient) -> str:
        """
        Generate appropriate next question based on missing field
        
        Args:
            field_name: Name of missing field
            patient: Current patient profile
        
        Returns:
            Interview question string
        """
        name = patient.name or "there"
        
        question_template = PROFILING_QUESTIONS.get(field_name, "")
        
        # Format with patient name if available
        if "{name}" in question_template:
            return question_template.format(name=name)
        
        return question_template


class DietitianNode:
    """
    Clinical Dietitian - Provides evidence-based nutrition advice
    
    Responsibilities:
    1. Retrieve patient context from database
    2. Query CLaRa retrieval engine with patient-aware filtering
    3. Generate personalized, safe nutrition advice
    4. Explain contraindications when relevant
    """
    
    # Initialize retriever
    retriever = ClaraRetriever()
    
    @staticmethod
    def process(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process nutrition question in Dietitian mode
        
        Args:
            state: Current conversation state
        
        Returns:
            Updated state with agent_response
        """
        phone_number = state["phone_number"]
        user_question = state["user_message"]
        
        logger.info(f"👨‍⚕️ Dietitian Node processing for {phone_number}")
        
        db = SessionLocal()
        try:
            # Get patient profile
            patient = PatientCRUD.get_patient_by_phone(db, phone_number)
            
            if not patient or patient.profiling_status != ProfilingStatus.COMPLETE:
                # Should not happen if routing is correct, but safety check
                logger.warning(f"⚠️ Incomplete profile accessed in Dietitian mode")
                state["agent_response"] = ERROR_MESSAGES["profile_incomplete"]
                state["next_mode"] = "nurse"
                return state
            
            # Get patient context for retrieval
            patient_context = patient.to_context_string()
            
            # Query CLaRa retriever with patient context
            try:
                retrieved_docs = DietitianNode.retriever.search(
                    query=user_question,
                    patient_context=patient_context,
                    top_k=5
                )
                
                # Format retrieved docs for prompt
                retrieved_text = "\n\n".join([
                    f"[Source {i+1}]: {doc}"
                    for i, doc in enumerate(retrieved_docs)
                ])
                
            except Exception as e:
                logger.error(f"❌ Retrieval error: {e}")
                retrieved_text = "Error accessing knowledge base."
            
            # Generate response using LLM with Dietitian prompt + retrieved docs
            response = DietitianNode._generate_dietitian_response(
                user_question=user_question,
                patient_context=patient_context,
                retrieved_docs=retrieved_text
            )
            
            state["agent_response"] = response
            state["next_mode"] = "dietitian"
            return state
            
        finally:
            db.close()
    
    @staticmethod
    def _generate_dietitian_response(
        user_question: str,
        patient_context: str,
        retrieved_docs: str
    ) -> str:
        """
        Generate personalized nutrition advice using LLM
        
        Args:
            user_question: User's nutrition question
            patient_context: Patient health profile
            retrieved_docs: Retrieved medical literature
        
        Returns:
            Dietitian response string
        """
        prompt = f"""{DIETITIAN_PROMPT}

**Patient Profile:**
{patient_context}

**Retrieved Medical Knowledge:**
{retrieved_docs}

**Patient Question:**
{user_question}

Provide a comprehensive, patient-specific answer. Consider their medical conditions, medications, and restrictions. Explain contraindications clearly."""
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.error(f"❌ Dietitian response generation failed: {e}")
            return ERROR_MESSAGES["general_error"]
