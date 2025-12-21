"""
Flask Webhook Server for WhatsApp (Twilio Integration)

Handles incoming WhatsApp messages, implements debounce logic,
and triggers the agentic brain.
"""

import os
import asyncio
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
from loguru import logger

from src.server.debounce import DebounceManager
from src.database.schema import SessionLocal
# Agent will be imported once implemented
# from src.agent.graph import agent_orchestrator

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
DEBOUNCE_SECONDS = float(os.getenv("MESSAGE_DEBOUNCE_SECONDS", "3"))

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize debounce manager
debounce_manager = DebounceManager(debounce_seconds=DEBOUNCE_SECONDS)

# Event loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


async def trigger_agent(phone_number: str, aggregated_text: str):
    """
    Callback triggered after debounce period expires
    
    This function:
    1. Receives aggregated user input
    2. Invokes the LangGraph agent orchestrator
    3. Sends agent response back via Twilio
    
    Args:
        phone_number: User's WhatsApp number
        aggregated_text: Debounced and aggregated message text
    """
    logger.info(f"🤖 Triggering agent for {phone_number}: '{aggregated_text}'")
    
    try:
        # Import agent orchestrator
        from src.agent.graph import agent_orchestrator
        
        # Invoke the agent
        agent_response = await agent_orchestrator(phone_number, aggregated_text)
        
        # Send response via Twilio
        send_whatsapp_message(phone_number, agent_response)
        
    except Exception as e:
        logger.error(f"❌ Error in agent processing: {e}")
        send_whatsapp_message(
            phone_number,
            "⚠️ Sorry, I encountered an error. Please try again."
        )


def send_whatsapp_message(to_number: str, message_text: str):
    """
    Send WhatsApp message via Twilio
    
    Args:
        to_number: Recipient phone number (with whatsapp: prefix)
        message_text: Text to send
    """
    try:
        # Ensure number has whatsapp: prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_text,
            to=to_number
        )
        logger.success(f"📤 Sent message to {to_number}: SID={message.sid}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send WhatsApp message: {e}")


@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Twilio WhatsApp webhook endpoint
    
    Receives incoming messages and adds them to debounce buffer
    """
    try:
        # Extract data from Twilio request
        incoming_msg = request.values.get("Body", "").strip()
        from_number = request.values.get("From", "")
        
        logger.info(f"📨 Webhook received: From={from_number}, Message='{incoming_msg}'")
        
        if not incoming_msg:
            logger.warning("⚠️ Received empty message")
            return Response(status=200)
        
        # Add message to debounce buffer (async)
        asyncio.run_coroutine_threadsafe(
            debounce_manager.add_message(from_number, incoming_msg, trigger_agent),
            loop
        )
        
        # Return empty response (no immediate reply)
        # The actual reply will be sent after debounce via trigger_agent()
        resp = MessagingResponse()
        return str(resp), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return Response(status=500)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "NutriBot WhatsApp Webhook"}, 200


@app.route("/debug/buffer/<phone_number>", methods=["GET"])
def debug_buffer(phone_number: str):
    """
    Debug endpoint to inspect buffer status
    
    Usage: GET /debug/buffer/whatsapp:+1234567890
    """
    # Add whatsapp: prefix if missing
    if not phone_number.startswith("whatsapp:"):
        phone_number = f"whatsapp:{phone_number}"
    
    status = debounce_manager.get_buffer_status(phone_number)
    
    if status:
        return status, 200
    else:
        return {"error": "No buffer found for this number"}, 404


def start_async_loop():
    """Start the async event loop in a separate thread"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


if __name__ == "__main__":
    import threading
    
    # Start async loop in background thread
    loop_thread = threading.Thread(target=start_async_loop, daemon=True)
    loop_thread.start()
    
    logger.info("🚀 Starting NutriBot WhatsApp Webhook Server...")
    logger.info(f"📱 WhatsApp Number: {TWILIO_WHATSAPP_NUMBER}")
    logger.info(f"⏱️ Debounce Period: {DEBOUNCE_SECONDS} seconds")
    
    # Run Flask app
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "True").lower() == "true"
    )
