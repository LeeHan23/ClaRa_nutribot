# NutriBot: Proprietary Agentic Medical RAG System

## Overview
NutriBot is a proprietary, agentic medical RAG system that acts as a Clinical Dietitian. It interviews patients via WhatsApp to build structured health profiles, then uses Apple's CLaRa framework to provide safe, evidence-based nutrition advice tailored to each patient's unique medical context.

## Core Features

### 🤖 Agentic State Machine
- **Intake Nurse Mode**: Conducts empathetic patient interviews to gather medical history
- **Dietitian Mode**: Provides expert nutrition advice based on complete patient profiles
- Powered by LangGraph for robust state management

### 💬 Fluid WhatsApp UX
- **3-Second Debounce**: Aggregates rapid user messages into coherent prompts
- Prevents fragmented responses and improves conversation flow
- Built on Twilio WhatsApp API

### 🧠 Proprietary Retrieval Engine
- **CLaRa Framework**: Apple's contextual language reasoning architecture
- **Medical Safety**: Context-aware filtering (e.g., high potassium contraindicated for CKD patients)
- Custom PDF ingestion pipeline for medical/dietetics literature

### 🗄️ Patient Database
- Persistent SQLite/PostgreSQL storage
- Structured patient profiles with medical conditions, medications, and allergies
- Profiling status tracking (IN_PROGRESS, COMPLETE)

## Architecture
```mermaid
graph TD
    %% Global Styles
    classDef input fill:#fff,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef gateway fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef logic fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef data fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef term fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    %% --- ZONE 1: INTERACTION ---
    subgraph Z1 [Zone 1: Interaction Layer]
        Patient(Patient) ::: input
        WA[WhatsApp / Twilio] ::: input
        Flask[Flask Server] ::: gateway
        
        Patient -->|Sends short texts| WA
        WA -->|Webhook POST| Flask
    end

    %% --- ZONE 2: GATEWAY ---
    subgraph Z2 [Zone 2: The Gateway]
        Debounce{Message<br/>Debouncer} ::: gateway
        Agg[Aggregate Texts<br/>Wait 3s] ::: gateway
        Query[/Merged User Query/] ::: gateway

        Flask -->|Raw Stream| Debounce
        Debounce -->|Timeout| Agg
        Agg --> Query
    end

    %% --- ZONE 3: AGENTIC BRAIN ---
    subgraph Z3 [Zone 3: Agentic Brain - LangGraph]
        Check{Profile Status?} ::: logic
        
        %% Path A: Incomplete Profile
        Nurse[👩‍⚕️ Nurse Node] ::: logic
        GenQ[Generate Interview Q] ::: logic
        
        %% Path B: Complete Profile
        Retrieval[Retrieval Call] ::: term
        Dietitian[🍎 Dietitian Node] ::: logic
        
        Final[Final Response] ::: term

        Query --> Check
        Check -->|Incomplete| Nurse
        Nurse -->|Identify Missing Data| GenQ
        GenQ --> Final
        
        Check -->|Complete| Retrieval
        Retrieval -->|Context + Query| Dietitian
        Dietitian -->|Safe Advice| Final
    end

    %% --- ZONE 4: PROPRIETARY DATA ---
    subgraph Z4 [Zone 4: Data & Knowledge Engine]
        direction TB
        SQL[(Local SQL DB<br/>Patient Profiles)] ::: data
        Context(Inject Medical Context<br/>e.g. Diabetes) ::: data
        
        PDF[Raw Medical PDFs] ::: data
        Vector[Compressed PDF Vectors] ::: data
        Engine[⚡ CLaRa Engine<br/>Phi-4-mini + LoRA] ::: data
        
        %% RAG Internal Flow
        PDF -->|Offline Compression| Vector
        Vector <--> Engine
    end

    %% --- CROSS-ZONE CONNECTIONS ---
    
    %% Nurse reads/writes to DB
    Nurse <-->|Read/Write Profile| SQL
    
    %% DB injects context into RAG call
    SQL -.-> Context
    Context -.-> Retrieval
    
    %% RAG Engine feeds Retrieval
    Engine <-->|Continuous Latent Search| Retrieval

    %% Feedback Loop
    Final -->|Send Message| WA
```

## Directory Structure

```
ClaRa_nutribot/
├── src/
│   ├── server/          # Flask/FastAPI webhook
│   │   ├── webhook.py   # Twilio webhook handler
│   │   └── debounce.py  # MessageBuffer class
│   ├── agent/           # LangGraph state machine
│   │   ├── graph.py     # Agentic brain
│   │   ├── nodes.py     # Nurse & Dietitian nodes
│   │   └── prompts.py   # System prompts
│   ├── database/        # Patient profiles
│   │   ├── schema.py    # SQLAlchemy models
│   │   └── crud.py      # Database operations
│   └── retriever/       # CLaRa integration
│       ├── clara_engine.py
│       └── pdf_loader.py
├── data/
│   ├── pdfs/            # Medical literature
│   └── clara_vectors/   # Compressed memory tokens
├── requirements.txt
├── .env.template
└── README.md
```

## Setup

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.template .env
# Edit .env with your Twilio credentials and API keys
```

### 3. Initialize Database
```bash
python -m src.database.schema
```

### 4. Add Medical Literature
```bash
# Place PDF files in data/pdfs/
# Run ingestion pipeline
python -m src.retriever.pdf_loader
```

### 5. Run Server
```bash
python -m src.server.webhook
```

## Usage

### Patient Onboarding Flow
1. User sends WhatsApp message to bot
2. Bot enters **Nurse Mode** and asks profiling questions:
   - "What medical conditions do you have?"
   - "Are you taking any medications?"
   - "Do you have any food allergies?"
3. Once profile is complete, bot switches to **Dietitian Mode**
4. User can now ask nutrition questions

### Example Conversation
```
User: "Hi, I need nutrition advice"

Bot (Nurse): "Hello! I'm your Clinical Dietitian. To provide safe, 
personalized advice, I need to understand your health first. Do you 
have any medical conditions I should know about?"

User: "I have chronic kidney disease stage 3"

Bot (Nurse): "Thank you for sharing. Are you currently taking any 
medications?"

User: "Warfarin and lisinopril"

Bot (Nurse): "Got it. Do you have any food allergies or intolerances?"

User: "No allergies"

Bot (Dietitian): "Perfect! Your profile is complete. I'm ready to 
help with any nutrition questions you have."

User: "Can I eat spinach?"

Bot (Dietitian): "⚠️ I recommend limiting spinach. Here's why:
1. High Potassium: Spinach is rich in potassium, which your kidneys 
   may struggle to filter with CKD stage 3.
2. Vitamin K Interaction: Since you're on Warfarin, high vitamin K 
   foods like spinach can interfere with your medication.

Better alternatives: Cucumbers, bell peppers, or cauliflower (lower 
potassium and vitamin K). Always consult your doctor before major 
dietary changes."
```

## Safety Features

### Contraindication Filtering
- **CKD Patients**: Filters high-potassium advice
- **Warfarin Users**: Warns about high vitamin K foods
- **Diabetes**: Prioritizes low-glycemic recommendations
- Context is passed from patient profile to retriever

### Empathetic Persona
- System prompts enforce Clinical Dietitian tone
- No generic "search results" - only interpreted medical advice
- Always recommends consulting healthcare providers

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Messaging** | Twilio WhatsApp API |
| **Web Framework** | Flask / FastAPI |
| **State Machine** | LangGraph |
| **LLM** | OpenAI GPT-4 Turbo |
| **Retrieval** | Apple CLaRa (Phi-4-mini) |
| **Database** | SQLAlchemy (SQLite/PostgreSQL) |
| **PDF Processing** | pypdf, pdfplumber |
| **Embeddings** | sentence-transformers |

## Development Roadmap

- [x] Project scaffolding
- [ ] Database schema implementation
- [ ] Debounce webhook server
- [ ] LangGraph agent brain
- [ ] CLaRa retriever wrapper
- [ ] PDF ingestion pipeline
- [ ] End-to-end testing
- [ ] Deployment guide

## License
Proprietary - All Rights Reserved

## Support
For questions or issues, contact the AI Systems Architecture team.
