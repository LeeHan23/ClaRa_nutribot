"""
LangGraph State Machine - The Agentic Brain

Implements the state graph that routes between Intake Nurse and Clinical Dietitian modes.
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from loguru import logger

from src.agent.nodes import IntakeNurseNode, DietitianNode
from src.database.schema import SessionLocal, ProfilingStatus
from src.database.crud import PatientCRUD


class AgentState(TypedDict):
    """
    State schema for the LangGraph agent
    
    Fields:
        phone_number: User's WhatsApp number
        user_message: Current user input
        agent_response: Response to send back
        conversation_history: List of previous messages
        next_mode: Which node to visit next ("nurse" or "dietitian")
    """
    phone_number: str
    user_message: str
    agent_response: str
    conversation_history: list
    next_mode: str


def route_to_mode(state: AgentState) -> str:
    """
    Routing function - decides which node to execute next
    
    Logic:
    1. Check patient profile status in database
    2. If profiling IN_PROGRESS or NOT_STARTED → route to Nurse
    3. If profiling COMPLETE → route to Dietitian
    
    Args:
        state: Current agent state
    
    Returns:
        "nurse" or "dietitian"
    """
    phone_number = state["phone_number"]
    
    db = SessionLocal()
    try:
        patient = PatientCRUD.get_or_create_patient(db, phone_number)
        
        if patient.profiling_status == ProfilingStatus.COMPLETE:
            logger.info(f"🔀 Routing {phone_number} → Dietitian (profile complete)")
            return "dietitian"
        else:
            logger.info(f"🔀 Routing {phone_number} → Nurse (profiling needed)")
            return "nurse"
    finally:
        db.close()


# Build the state graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("nurse", lambda state: IntakeNurseNode.process(state))
workflow.add_node("dietitian", lambda state: DietitianNode.process(state))

# Set entry point with conditional routing
workflow.set_conditional_entry_point(
    route_to_mode,
    {
        "nurse": "nurse",
        "dietitian": "dietitian"
    }
)

# Add edges from nodes to END
workflow.add_edge("nurse", END)
workflow.add_edge("dietitian", END)

# Compile the graph
agent_graph = workflow.compile()


async def agent_orchestrator(phone_number: str, user_message: str) -> str:
    """
    Main entry point for the agentic system
    
    Called by the webhook after debounce period expires.
    
    Args:
        phone_number: User's WhatsApp number
        user_message: Aggregated user input
    
    Returns:
        Agent's response to send via WhatsApp
    """
    logger.info(f"🧠 Agent orchestrator invoked for {phone_number}")
    logger.debug(f"User message: '{user_message}'")
    
    # Initialize state
    initial_state: AgentState = {
        "phone_number": phone_number,
        "user_message": user_message,
        "agent_response": "",
        "conversation_history": [],  # TODO: Load from database if needed
        "next_mode": ""
    }
    
    try:
        # Run the graph
        result = await agent_graph.ainvoke(initial_state)
        
        response = result.get("agent_response", "I'm sorry, I encountered an error.")
        
        logger.success(f"✅ Agent response generated: {response[:100]}...")
        return response
        
    except Exception as e:
        logger.error(f"❌ Agent orchestrator error: {e}")
        return "⚠️ I'm sorry, I encountered an error. Please try again."


# For testing the graph structure
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        """Test the agent with a mock conversation"""
        # Test 1: New patient (should route to Nurse)
        response1 = await agent_orchestrator(
            phone_number="whatsapp:+1234567890",
            user_message="Hi, I need nutrition advice"
        )
        print(f"\n🧪 Test 1 - New Patient:\n{response1}\n")
        
        # Test 2: Provide name
        response2 = await agent_orchestrator(
            phone_number="whatsapp:+1234567890",
            user_message="My name is John"
        )
        print(f"🧪 Test 2 - Name Provided:\n{response2}\n")
    
    asyncio.run(test_agent())
