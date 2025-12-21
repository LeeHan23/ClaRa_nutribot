# NutriBot Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit .env and add your OpenAI API key
# Required: OPENAI_API_KEY
# Optional (for WhatsApp): TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
```

**Minimum required configuration for testing:**
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Run Component Tests

Test the system without needing WhatsApp setup:

```bash
python test_components.py
```

This will test:
- ✅ Database operations
- ✅ CLaRa retriever with safety filtering
- ✅ Agent conversation flow (Nurse → Dietitian)

### 4. Start the Server

```bash
python run.py
```

The server will start at `http://localhost:5000`

---

## Testing the System

### Option 1: Component Tests (No WhatsApp Required)

```bash
python test_components.py
```

This simulates a complete conversation showing the Nurse → Dietitian transition.

### Option 2: Manual Webhook Testing

Start the server, then in another terminal:

```bash
curl -X POST http://localhost:5000/webhook/whatsapp \
  -d "From=whatsapp:+1234567890" \
  -d "Body=Hi, I need nutrition advice"
```

Wait 3 seconds (debounce period), then check server logs for the response.

### Option 3: Full WhatsApp Integration

1. **Get Twilio Credentials:**
   - Sign up at https://www.twilio.com/try-twilio
   - Get WhatsApp Sandbox number
   - Copy Account SID and Auth Token to `.env`

2. **Expose Local Server with ngrok:**
   ```bash
   ngrok http 5000
   ```

3. **Configure Twilio Webhook:**
   - Go to Twilio Console → WhatsApp Sandbox Settings
   - Set webhook URL to: `https://your-ngrok-url.ngrok.io/webhook/whatsapp`

4. **Send WhatsApp Message:**
   - Send to your Twilio WhatsApp number
   - Bot will respond after 3-second debounce

---

## System Architecture

```
WhatsApp Message
       ↓
Twilio Webhook → /webhook/whatsapp
       ↓
MessageBuffer (3s debounce)
       ↓
Agent Orchestrator
       ↓
   ┌───────────────┐
   │ Check Profile │
   └───────┬───────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐   ┌─────────────┐
│ Nurse  │   │  Dietitian  │
│  Node  │   │    Node     │
└────┬───┘   └──────┬──────┘
     │              │
     │              ▼
     │       ┌──────────────┐
     │       │ ClaraRetriever│
     │       │ (Safety Filter)│
     │       └──────────────┘
     │              │
     └──────┬───────┘
            ▼
       LLM Response
            ↓
    Twilio → WhatsApp
```

---

## Directory Structure

```
ClaRa_nutribot/
├── src/
│   ├── server/
│   │   ├── webhook.py         # Flask webhook handler
│   │   └── debounce.py        # 3-second message buffer
│   ├── agent/
│   │   ├── graph.py           # LangGraph state machine
│   │   ├── nodes.py           # Nurse & Dietitian nodes
│   │   └── prompts.py         # System prompts
│   ├── database/
│   │   ├── schema.py          # Patient profile model
│   │   └── crud.py            # Database operations
│   ├── retriever/
│   │   ├── clara_engine.py    # Mock CLaRa retriever
│   │   └── pdf_loader.py      # PDF ingestion
│   └── config.py              # Configuration
├── data/
│   ├── pdfs/                  # Medical literature
│   ├── clara_vectors/         # (Future) Vector store
│   └── nutribot.db            # SQLite database
├── logs/
│   └── nutribot.log           # Application logs
├── run.py                     # Main entry point
├── test_components.py         # Test script
├── requirements.txt
└── .env                       # Your configuration
```

---

## Example Conversation

**User:** Hi, I need nutrition advice

**Bot (Nurse):** Hello! I'm NutriBot, your Clinical Dietitian assistant. To provide safe, personalized advice, I'd like to learn about your health first. What's your name?

**User:** Sarah

**Bot (Nurse):** Thank you, Sarah! Do you have any medical conditions I should know about?

**User:** I have chronic kidney disease stage 3

**Bot (Nurse):** Are you currently taking any medications?

**User:** Warfarin and lisinopril

**Bot (Nurse):** Do you follow any dietary restrictions?

**User:** I'm vegetarian

**Bot (Nurse):** Finally, do you have any food allergies?

**User:** No allergies

**Bot (Dietitian):** Perfect! Your profile is complete. ✅ I'm ready to help with any nutrition questions you have. What would you like to know?

**User:** Can I eat spinach?

**Bot (Dietitian):** ⚠️ I recommend limiting spinach. Here's why:

1. **High Potassium Risk**: Spinach contains significant potassium. With CKD stage 3, your kidneys may struggle to filter excess potassium.

2. **Warfarin Interaction**: Spinach is high in vitamin K, which can interfere with your Warfarin medication.

**Better alternatives**: Bell peppers, cauliflower, or cucumbers (lower potassium and vitamin K).

Always consult your nephrologist before major dietary changes.

---

## Troubleshooting

### "ModuleNotFoundError"
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Configuration validation failed: OPENAI_API_KEY is not set"
```bash
# Edit .env file
nano .env

# Add your OpenAI API key:
OPENAI_API_KEY=sk-your-actual-key-here
```

### "No module named 'langgraph'"
```bash
# Install specific version
pip install langgraph==0.2.0
```

### Database errors
```bash
# Delete and recreate database
rm data/nutribot.db
python run.py
```

---

## Next Steps

### Current Status: ✅ Mock Retriever
The system uses a mock CLaRa retriever with:
- 12 pre-loaded nutrition documents
- Medical safety filtering (CKD, Warfarin, etc.)
- Simple keyword-based search

### Future: 🚀 Full CLaRa Integration

Once you Train CLaRa on Google Colab:

1. Download trained model weights
2. Update `src/retriever/clara_engine.py`:
   ```python
   from transformers import AutoModel
   
   model = AutoModel.from_pretrained(
       "path/to/your/trained/clara/model",
       trust_remote_code=True
   ).to('cuda')
   ```

3. Replace `_mock_semantic_search()` with actual CLaRa inference
4. Add PDF documents to `data/pdfs/`
5. Run PDF ingestion pipeline

The interface is designed to be swap-compatible!

---

## Support

For issues or questions:
1. Check logs: `tail -f logs/nutribot.log`
2. Run tests: `python test_components.py`
3. Enable debug logging: Set `LOG_LEVEL=DEBUG` in `.env`
