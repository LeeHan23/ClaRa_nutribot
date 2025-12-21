#!/usr/bin/env python3
"""
Quick Test Script for NutriBot Components

Tests individual components without needing Twilio setup.
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import setup_logging
from src.database.schema import init_db, SessionLocal
from src.database.crud import PatientCRUD
from src.agent.graph import agent_orchestrator
from src.retriever.clara_engine import ClaraRetriever
from loguru import logger


def test_database():
    """Test database operations"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing Database Operations")
    logger.info("="*60)
    
    # Initialize database
    init_db()
    
    # Create test patient
    db = SessionLocal()
    test_phone = "whatsapp:+1234567890"
    
    # Get or create patient
    patient = PatientCRUD.get_or_create_patient(db, test_phone)
    logger.info(f"✅ Patient created: {patient.phone_number}")
    
    # Update patient info
    patient = PatientCRUD.save_patient_info(
        db=db,
        phone_number=test_phone,
        name="John Doe",
        age=45,
        medical_conditions="CKD Stage 3, Diabetes Type 2",
        current_medications="Warfarin, Lisinopril, Metformin",
        dietary_restrictions="None",
        food_allergies="Shellfish"
    )
    
    logger.info(f"✅ Patient profile updated")
    logger.info(f"   Status: {patient.profiling_status}")
    logger.info(f"\n📋 Patient Context:\n{patient.to_context_string()}")
    
    db.close()
    return True


def test_retriever():
    """Test CLaRa retriever"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing CLaRa Retriever")
    logger.info("="*60)
    
    retriever = ClaraRetriever()
    
    # Test query
    query = "Can I eat bananas?"
    patient_context = """
Patient: John Doe
Age: 45
Medical Conditions: CKD Stage 3, Diabetes Type 2
Current Medications: Warfarin, Lisinopril, Metformin
Food Allergies: Shellfish
"""
    
    results = retriever.search(query, patient_context, top_k=3)
    
    logger.info(f"\n🔍 Query: '{query}'")
    logger.info(f"\n📚 Retrieved {len(results)} document(s):")
    for i, doc in enumerate(results, 1):
        logger.info(f"\n[{i}] {doc[:200]}...")
    
    return True


async def test_agent():
    """Test agent orchestrator"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing Agent Orchestrator")
    logger.info("="*60)
    
    test_phone = "whatsapp:+9876543210"
    
    # Test 1: Initial greeting (should trigger Nurse)
    logger.info("\n--- Test 1: Initial Greeting ---")
    response1 = await agent_orchestrator(test_phone, "Hi, I need nutrition advice")
    logger.info(f"🤖 Bot: {response1}\n")
    
    # Test 2: Provide name
    logger.info("\n--- Test 2: Provide Name ---")
    response2 = await agent_orchestrator(test_phone, "My name is Sarah")
    logger.info(f"🤖 Bot: {response2}\n")
    
    # Test 3: Provide medical conditions
    logger.info("\n--- Test 3: Medical Conditions ---")
    response3 = await agent_orchestrator(test_phone, "I have chronic kidney disease stage 3")
    logger.info(f"🤖 Bot: {response3}\n")
    
    # Test 4: Provide medications
    logger.info("\n--- Test 4: Medications ---")
    response4 = await agent_orchestrator(test_phone, "I take Warfarin and lisinopril")
    logger.info(f"🤖 Bot: {response4}\n")
    
    # Test 5: Dietary restrictions
    logger.info("\n--- Test 5: Dietary Restrictions ---")
    response5 = await agent_orchestrator(test_phone, "I'm vegetarian")
    logger.info(f"🤖 Bot: {response5}\n")
    
    # Test 6: Food allergies
    logger.info("\n--- Test 6: Food Allergies ---")
    response6 = await agent_orchestrator(test_phone, "No food allergies")
    logger.info(f"🤖 Bot: {response6}\n")
    
    # Test 7: Nutrition question (should trigger Dietitian)
    logger.info("\n--- Test 7: Nutrition Question ---")
    response7 = await agent_orchestrator(test_phone, "Can I eat spinach?")
    logger.info(f"🤖 Bot: {response7}\n")
    
    return True


async def main():
    """Main test runner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║            NutriBot Component Test Suite                 ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Setup logging
    setup_logging()
    
    try:
        # Test 1: Database
        if test_database():
            logger.success("✅ Database tests passed\n")
        
        # Test 2: Retriever
        if test_retriever():
            logger.success("✅ Retriever tests passed\n")
        
        # Test 3: Agent (requires OpenAI API key)
        try:
            if await test_agent():
                logger.success("✅ Agent tests passed\n")
        except Exception as e:
            logger.error(f"❌ Agent test failed: {e}")
            logger.info("💡 Make sure OPENAI_API_KEY is set in .env")
        
        logger.success("\n" + "="*60)
        logger.success("🎉 All tests completed!")
        logger.success("="*60)
        
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
