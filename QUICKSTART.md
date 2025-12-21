# NutriBot Quick Reference

## 🚀 Quick Start (3 Commands)

```bash
# 1. Set your OpenAI API key
echo "OPENAI_API_KEY=sk-your-actual-key-here" >> .env

# 2. Install dependencies (with virtual environment)
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 3. Run tests
python test_components.py
```

---

## 📁 Project Files

### Core Components
| File | Purpose | Lines |
|------|---------|-------|
| [run.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/run.py) | Main entry point - start server | 98 |
| [test_components.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/test_components.py) | Test all components | 163 |
| [.env](file:///Volumes/T7%20Shield/ClaRa_nutribot/.env) | Configuration (ADD YOUR API KEY HERE) | - |

### Server Layer
| File | Purpose |
|------|---------|
| [src/server/webhook.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/server/webhook.py) | Flask webhook handler |
| [src/server/debounce.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/server/debounce.py) | 3-second message aggregation |

### Agent Layer
| File | Purpose |
|------|---------|
| [src/agent/graph.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/agent/graph.py) | LangGraph state machine |
| [src/agent/nodes.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/agent/nodes.py) | Nurse + Dietitian nodes |
| [src/agent/prompts.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/agent/prompts.py) | System prompts |

### Data Layer
| File | Purpose |
|------|---------|
| [src/database/schema.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/database/schema.py) | Patient profile model |
| [src/database/crud.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/database/crud.py) | Database operations |

### Retrieval Layer
| File | Purpose |
|------|---------|
| [src/retriever/clara_engine.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/retriever/clara_engine.py) | Mock CLaRa retriever (SWAP FOR REAL MODEL) |
| [src/retriever/pdf_loader.py](file:///Volumes/T7%20Shield/ClaRa_nutribot/src/retriever/pdf_loader.py) | PDF document ingestion |

---

## 🧪 Testing Commands

```bash
# Test all components (database, retriever, agent)
python test_components.py

# Start the server
python run.py

# Test webhook manually (in another terminal)
curl -X POST http://localhost:5000/webhook/whatsapp \
  -d "From=whatsapp:+1234567890" \
  -d "Body=Hi there"

# Initialize database only
python -m src.database.schema

# Test PDF loader
python -m src.retriever.pdf_loader
```

---

## 🔧 Configuration (.env)

**Minimum for testing:**
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

**Full configuration:**
```env
# OpenAI (REQUIRED)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# Twilio WhatsApp (Optional for testing)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Server
PORT=5000
MESSAGE_DEBOUNCE_SECONDS=3

# Logging
LOG_LEVEL=INFO
```

---

## 🎯 Key Features

### ✅ Implemented
- [x] 3-second debounce for message aggregation
- [x] LangGraph state machine (Nurse → Dietitian)
- [x] Patient profile database with SQLite
- [x] Medical safety filtering (CKD, Warfarin, etc.)
- [x] Mock CLaRa retriever with 12 nutrition documents
- [x] Empathetic Clinical Dietitian persona
- [x] Async webhook processing
- [x] Comprehensive logging

### 🚧 To Be Added (Later)
- [ ] Full CLaRa model integration (Train on Google Colab)
- [ ] WhatsApp deployment (Requires Twilio setup)
- [ ] PDF medical literature ingestion
- [ ] Vector database for embeddings
- [ ] Admin dashboard

---

## 🔄 Agent Flow

```
New Message → Debounce (3s) → Agent Orchestrator
                                       ↓
                              Check Profile Status
                                       ↓
                    ┌──────────────────┴──────────────────┐
                    │                                     │
             Profile Incomplete                   Profile Complete
                    │                                     │
                    ▼                                     ▼
            Intake Nurse Node                    Dietitian Node
                    │                                     │
            (Ask next question)                  (Query CLaRa Retriever)
                    │                                     │
            (Extract & store info)              (Apply safety filters)
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                                  LLM Response
                                       ↓
                               Send via WhatsApp
```

---

## 🚨 Medical Safety Filters

| Patient Condition | Filters Out |
|-------------------|-------------|
| **CKD (Chronic Kidney Disease)** | High potassium foods (bananas, spinach, avocados) |
| **Warfarin medication** | High vitamin K foods (kale, broccoli, spinach) |
| **Diabetes** | High glycemic index foods |
| **Hypertension** | High sodium foods |
| **Vegetarian** | Meat, chicken, fish |

**Example**:
- Patient: CKD Stage 3 + Warfarin
- Query: "Can I eat spinach?"
- System: ❌ Filters out spinach (high K + high Vit K)
- System: ✅ Suggests cauliflower, bell peppers instead

---

## 📊 Database Schema

**PatientProfile Table**:
```
phone_number        (Primary Key)
name               
age                
medical_conditions  (e.g., "CKD Stage 3, Diabetes")
current_medications (e.g., "Warfarin, Lisinopril")
dietary_restrictions (e.g., "Vegetarian")
food_allergies      (e.g., "Shellfish")
profiling_status    (NOT_STARTED | IN_PROGRESS | COMPLETE)
created_at         
updated_at         
```

**Location**: `data/nutribot.db` (SQLite)

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate` |
| `OPENAI_API_KEY not set` | Edit `.env` and add your key |
| `No module named 'langgraph'` | `pip install langgraph==0.2.0` |
| Database errors | Delete `data/nutribot.db` and restart |
| Import errors | Make sure you're in project root directory |

---

## 📚 Documentation

- [README.md](file:///Volumes/T7%20Shield/ClaRa_nutribot/README.md) - Project overview
- [SETUP.md](file:///Volumes/T7%20Shield/ClaRa_nutribot/SETUP.md) - Detailed setup guide
- [walkthrough.md](file:///Users/leehan/.gemini/antigravity/brain/f0671f7f-6176-4db2-8367-60bc07c0467a/walkthrough.md) - Complete implementation walkthrough
- [task.md](file:///Users/leehan/.gemini/antigravity/brain/f0671f7f-6176-4db2-8367-60bc07c0467a/task.md) - Task checklist
- [implementation_plan.md](file:///Users/leehan/.gemini/antigravity/brain/f0671f7f-6176-4db2-8367-60bc07c0467a/implementation_plan.md) - Technical plan

---

## 🎓 Next Steps for You

### 1. **Test the System** (Today)
```bash
# Add your OpenAI key to .env
nano .env

# Run tests
python test_components.py

# Expected: See full conversation simulation
```

### 2. **Train Full CLaRa Model** (Google Colab)
```bash
# Clone CLaRa
git clone https://github.com/apple/ml-clara.git

# Prepare medical PDFs
# Run 3-stage training
# Download trained weights
```

### 3. **Integrate CLaRa Model** (After Training)
- Replace mock retriever in `src/retriever/clara_engine.py`
- Load trained model weights
- Interface is already compatible!

### 4. **Deploy to Production** (Optional)
- Set up Twilio WhatsApp Business API
- Deploy to cloud (Heroku/AWS/GCP)
- Switch to PostgreSQL
- Add monitoring

---

## 💡 Key Design Decisions

1. **Why debounce?** Users send fragmented messages → debounce creates coherent prompts
2. **Why LangGraph?** State machines are perfect for multi-step conversations
3. **Why mock retriever first?** Validate architecture before expensive CLaRa training
4. **Why safety filtering?** Medical advice requires contraindication awareness
5. **Why separate Nurse/Dietitian?** Different tasks require different prompts and tools

---

**Status**: ✅ System complete and ready for testing!

**Author**: AI Systems Architect (Antigravity)  
**Date**: 2025-12-16  
**Version**: 1.0 (Mock CLaRa)
