# CLaRa Model Training Guide for NutriBot

## Overview

This guide walks you through training Apple's CLaRa model on Google Colab and integrating it into your NutriBot system to replace the mock retriever with a real compressed document reasoning engine.

## What is CLaRa?

**CLaRa** (Continuous Latent Reasoning) is Apple's state-of-the-art RAG system that:
- Compresses documents 32x-64x while preserving semantics
- Unifies retrieval and generation in one model
- Achieves better accuracy than traditional RAG systems

**Training Stages**:
1. **Stage 1**: Compression pretraining (learns to compress documents)
2. **Stage 2**: Instruction tuning (fine-tunes for QA tasks)
3. **Stage 3**: End-to-end training (combines retrieval + generation)

---

## Prerequisites

### 1. Google Colab Setup

- **GPU Required**: T4 (free tier) or A100 (Colab Pro - $10/month recommended)
- **Storage**: ~15GB for model + data
- **Runtime**: 4-8 hours for basic training

### 2. Prepare Your Medical/Dietetics Data

You need training data in **JSONL format**. Two options:

#### Option A: Use Existing Medical Datasets (Easiest)
- **PubMedQA**: Medical question-answering dataset
- **MedQA**: Clinical reasoning dataset
- Download from HuggingFace

#### Option B: Create Custom Dataset from Your PDFs
- Extract text from PDFs in `data/pdfs/`
- Generate QA pairs using GPT-4
- Format as JSONL

---

## Step-by-Step Training Guide

### Phase 1: Google Colab Setup (30 minutes)

#### 1. Create New Colab Notebook

Go to: https://colab.research.google.com

Click: **New Notebook**

#### 2. Enable GPU

```
Runtime → Change runtime type → Hardware accelerator → T4 GPU → Save
```

#### 3. Install Dependencies

```python
# Cell 1: Install CLaRa and dependencies
!git clone https://github.com/apple/ml-clara.git
%cd ml-clara

!pip install -r requirements.txt
!pip install torch transformers datasets accelerate deepspeed flash-attn
```

#### 4. Mount Google Drive (for saving models)

```python
# Cell 2: Mount Drive
from google.colab import drive
drive.mount('/content/drive')

# Create directory for models
!mkdir -p /content/drive/MyDrive/nutribot_clara
```

---

### Phase 2: Data Preparation (1 hour)

#### Option A: Quick Start with PubMedQA

```python
# Cell 3: Download PubMedQA dataset
from datasets import load_dataset

# Load PubMedQA
dataset = load_dataset("pubmed_qa", "pqa_labeled")

# Convert to CLaRa format
import json

def convert_to_clara_format(example):
    return {
        "question": example["question"],
        "docs": [example["context"]["contexts"][0]],  # Use first context
        "gold_answer": example["long_answer"]
    }

# Convert and save
train_data = [convert_to_clara_format(ex) for ex in dataset["train"]]

with open("nutrition_train.jsonl", "w") as f:
    for item in train_data[:1000]:  # Use 1000 examples for speed
        f.write(json.dumps(item) + "\n")

print(f"✅ Created training data: {len(train_data)} examples")
```

#### Option B: Create Custom Dataset from Your PDFs

```python
# Cell 3 (Alternative): Generate QA pairs from PDFs
import openai
import pdfplumber
from pathlib import Path

openai.api_key = "your-openai-api-key"

def extract_pdf_text(pdf_path):
    """Extract text from PDF"""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n\n".join([page.extract_text() for page in pdf.pages])
    return text

def generate_qa_pairs(text, num_pairs=5):
    """Generate QA pairs using GPT-4"""
    prompt = f"""Given this nutrition/medical text, generate {num_pairs} question-answer pairs.
    
Text:
{text[:3000]}

Format each as JSON:
{{"question": "...", "answer": "..."}}

Generate {num_pairs} QA pairs:"""
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse response and return QA pairs
    return response.choices[0].message.content

# Process your PDFs
pdf_dir = Path("/content/drive/MyDrive/nutrition_pdfs")  # Upload PDFs here
qa_dataset = []

for pdf_file in pdf_dir.glob("*.pdf"):
    print(f"Processing {pdf_file.name}...")
    text = extract_pdf_text(pdf_file)
    
    # Generate 10 QA pairs per PDF
    qa_pairs = generate_qa_pairs(text, num_pairs=10)
    
    # Format for CLaRa
    for qa in qa_pairs:
        qa_dataset.append({
            "question": qa["question"],
            "docs": [text[:2000]],  # First 2000 chars as context
            "gold_answer": qa["answer"]
        })

# Save
with open("nutrition_train.jsonl", "w") as f:
    for item in qa_dataset:
        f.write(json.dumps(item) + "\n")

print(f"✅ Generated {len(qa_dataset)} QA pairs")
```

---

### Phase 3: Train CLaRa (4-8 hours)

#### Stage 1: Compression Pretraining

```python
# Cell 4: Stage 1 Training
!python openrlhf/cli/train_sft.py \
    --pretrain microsoft/phi-2 \
    --dataset nutrition_train.jsonl \
    --dataset_probs 1.0 \
    --train_batch_size 16 \
    --micro_train_batch_size 2 \
    --max_len 2048 \
    --max_epochs 3 \
    --learning_rate 1e-4 \
    --save_path /content/drive/MyDrive/nutribot_clara/stage1 \
    --save_steps 500 \
    --logging_steps 10 \
    --stage stage1 \
    --compress_rate 32 \
    --doc_max_length 256 \
    --mse_loss \
    --qa_loss \
    --zero_stage 2 \
    --bf16 \
    --flash_attn
```

**Expected runtime**: 2-3 hours on T4 GPU

#### Stage 2: Instruction Tuning

```python
# Cell 5: Stage 2 Training
!python openrlhf/cli/train_sft.py \
    --pretrain /content/drive/MyDrive/nutribot_clara/stage1 \
    --dataset nutrition_train.jsonl \
    --train_batch_size 16 \
    --micro_train_batch_size 2 \
    --max_len 2048 \
    --max_epochs 2 \
    --learning_rate 5e-5 \
    --save_path /content/drive/MyDrive/nutribot_clara/stage2 \
    --save_steps 500 \
    --stage stage1_2 \
    --generation_top_k 5 \
    --mse_loss \
    --do_eval_gen \
    --zero_stage 2 \
    --bf16 \
    --flash_attn
```

**Expected runtime**: 1-2 hours

#### Stage 3: End-to-End Training (Optional, Advanced)

```python
# Cell 6: Stage 3 Training (Optional)
!python openrlhf/cli/train_sft.py \
    --pretrain /content/drive/MyDrive/nutribot_clara/stage2 \
    --dataset nutrition_train.jsonl \
    --train_batch_size 8 \
    --micro_train_batch_size 1 \
    --max_len 1024 \
    --max_epochs 2 \
    --learning_rate 5e-6 \
    --save_path /content/drive/MyDrive/nutribot_clara/stage3 \
    --save_steps 500 \
    --stage stage2 \
    --generation_top_k 5 \
    --do_eval_gen \
    --zero_stage 2 \
    --bf16 \
    --flash_attn
```

**Expected runtime**: 2-4 hours

---

### Phase 4: Download Trained Model

```python
# Cell 7: Zip and download model
!zip -r /content/drive/MyDrive/nutribot_clara_stage2.zip /content/drive/MyDrive/nutribot_clara/stage2

print("✅ Model saved to Google Drive: nutribot_clara_stage2.zip")
print("Download it to your local machine!")
```

**Download from**: Google Drive → `nutribot_clara_stage2.zip`

---

## Phase 5: Integrate into NutriBot

### 1. Extract Model on Your Machine

```bash
cd "/Volumes/T7 Shield/ClaRa_nutribot"
mkdir -p models
unzip ~/Downloads/nutribot_clara_stage2.zip -d models/
mv models/content/drive/MyDrive/nutribot_clara/stage2 models/clara_trained
```

### 2. Update `src/retriever/clara_engine.py`

Replace the `ClaraRetriever.__init__()` method:

```python
# Around line 35-40 in clara_engine.py

def __init__(self, knowledge_base_path: Optional[str] = None):
    """Initialize CLaRa retriever with trained model"""
    self.knowledge_base_path = knowledge_base_path
    
    # Load trained CLaRa model
    from transformers import AutoModel
    import torch
    
    model_path = "./models/clara_trained"
    
    logger.info(f"🔥 Loading trained CLaRa model from {model_path}")
    
    self.model = AutoModel.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    
    # Move to GPU if available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    self.model = self.model.to(device)
    self.model.eval()
    
    logger.success(f"✅ CLaRa model loaded on {device}")
    
    # Load nutrition documents
    self.documents = self._load_documents()
```

### 3. Update `search()` Method

```python
# Around line 70-90 in clara_engine.py

def search(self, query: str, patient_context: str, top_k: int = 5) -> List[str]:
    """Search with real CLaRa model"""
    logger.info(f"🔍 Searching with trained CLaRa: '{query}'")
    
    # Extract contraindications
    contraindications = self._extract_contraindications(patient_context)
    logger.info(f"🚨 Detected contraindications: {contraindications}")
    
    # Prepare documents for CLaRa
    doc_list = [self.documents]  # List of document lists
    questions = [query]
    
    # Run CLaRa inference
    with torch.no_grad():
        output, topk_indices = self.model.generate_from_questions(
            questions=questions,
            documents=doc_list,
            max_new_tokens=128
        )
    
    # Get retrieved documents
    retrieved_docs = [self.documents[i] for i in topk_indices[0]]
    
    # Apply safety filters
    safe_docs = self._apply_safety_filters(
        [{"text": doc, "title": f"Doc {i}"} for i, doc in enumerate(retrieved_docs)],
        contraindications,
        patient_context
    )
    
    return safe_docs[:top_k]
```

### 4. Add Document Loader

```python
# Add this method to ClaraRetriever class

def _load_documents(self) -> List[str]:
    """Load nutrition documents from PDFs or database"""
    from src.retriever.pdf_loader import load_medical_literature
    
    # Try loading from PDFs first
    pdf_docs = load_medical_literature("./data/pdfs")
    
    if pdf_docs:
        logger.info(f"📚 Loaded {len(pdf_docs)} documents from PDFs")
        return [doc["text"] for doc in pdf_docs]
    
    # Fallback to mock knowledge base
    logger.warning("⚠️ No PDFs found, using mock knowledge base")
    return [doc["text"] for doc in self._build_mock_kb()]
```

### 5. Test the Integration

```bash
# Run tests with real CLaRa model
python test_components.py

# Start server
python run.py
```

---

## Simplified Quick Start (If Pressed for Time)

**Use Pre-trained CLaRa Model from HuggingFace**:

```python
# In src/retriever/clara_engine.py __init__()

from transformers import AutoModel

# Use Apple's pre-trained model (no training needed!)
self.model = AutoModel.from_pretrained(
    "apple/clara-stage2",  # Hypothetical - check HuggingFace
    trust_remote_code=True
)
```

*Note: Check https://huggingface.co/apple for available models*

---

## Cost Breakdown

| Option | Cost | Time | GPU |
|--------|------|------|-----|
| **Colab Free (T4)** | $0 | 8-12 hours | T4 |
| **Colab Pro (A100)** | $10/month | 4-6 hours | A100 |
| **Use Pre-trained** | $0 | 0 hours | None (CPU inference OK) |

---

## Next Steps

1. **Choose your path**:
   - Train custom model (most accurate for your domain)
   - Use pre-trained model (fastest to deploy)

2. **Prepare data**:
   - Gather nutrition/medical PDFs
   - OR use PubMedQA dataset

3. **Run training** on Google Colab

4. **Integrate trained model** using guide above

5. **Test with real medical queries**

---

## Support Files Created

Your NutriBot system already has:
- ✅ `src/retriever/clara_engine.py` - Interface ready for real model
- ✅ `src/retriever/pdf_loader.py` - PDF ingestion pipeline
- ✅ Safety filtering logic - Works with any retriever backend

**The entire system is designed to be swap-compatible!** Just drop in the trained model and everything else keeps working.

---

## Questions?

Common issues and solutions documented in troubleshooting section below.

### Troubleshooting

**Out of memory on Colab**:
```python
# Reduce batch size
--train_batch_size 8
--micro_train_batch_size 1
```

**Training too slow**:
```python
# Use smaller model
--pretrain microsoft/phi-2  # Instead of phi-4
--max_len 1024  # Reduce sequence length
```

**Model too large to download**:
```python
# Use Google Drive streaming
from google.colab import drive
drive.mount('/content/drive', force_remount=True)
```

Good luck! 🚀
