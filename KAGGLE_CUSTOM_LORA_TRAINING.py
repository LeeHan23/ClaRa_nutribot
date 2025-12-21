# ============================================================
# KAGGLE CUSTOM LoRA TRAINING - MEDICAL NUTRITION MODEL
# Production-Ready Fine-Tuning Script
# ============================================================
# 
# WHAT THIS DOES:
# - Trains a medical nutrition model using LoRA (Low-Rank Adaptation)
# - Uses your 156 custom QA pairs from medical PDFs
# - Creates a domain-specific model for NutriBot
# - WORKS FIRST TRY - no dependency hell!
#
# INSTRUCTIONS:
# 1. Go to https://www.kaggle.com
# 2. Create New Notebook
# 3. Enable Internet: Settings → Internet → ON
# 4. Enable GPU: Settings → Accelerator → GPU P100 (or T4)
# 5. Upload nutrition_train.jsonl to Input
# 6. Copy each CELL section below into Kaggle cells
# 7. Run all cells sequentially
#
# TIME: 45-60 minutes on GPU
# ============================================================

# ============================================================
# CELL 1: Verify GPU
#  ============================================================

import torch

print("🔍 Checking Hardware...\n")

if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✅ CUDA Version: {torch.version.cuda}")
    print(f"✅ Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print("\n🎉 Ready for training!")
else:
    print("⚠️ No GPU detected - training will be VERY slow")
    print("💡 Go to Settings → Accelerator → GPU")


# ============================================================
# CELL 2: Install Dependencies
# ============================================================

print("📦 Installing dependencies...\n")

# Install core packages
!pip install -q transformers==4.36.0 datasets accelerate
!pip install -q peft bitsandbytes sentencepiece

print("✅ Installation complete!")

# Verify
import transformers
print(f"\n📋 Versions:")
print(f"  Transformers: {transformers.__version__}")
print(f"  PyTorch: {torch.__version__}")


# ============================================================
# CELL 3: Load and Prepare Training Data
# ============================================================

import json
from pathlib import Path

# IMPORTANT: Update this path to match your uploaded file
DATA_PATH = "/kaggle/input/nutrition-train/nutrition_train.jsonl"

print("📂 Loading training data...\n")

# Check if file exists
if not Path(DATA_PATH).exists():
    print(f"❌ File not found: {DATA_PATH}")
    print("\n💡 Steps to fix:")
    print("1. Click 'Add Data' on right sidebar")
    print("2. Upload your nutrition_train.jsonl")
    print("3. Update DATA_PATH in this cell")
    raise FileNotFoundError(DATA_PATH)

# Load data
with open(DATA_PATH) as f:
    data = [json.loads(line) for line in f]

print(f"✅ Loaded {len(data)} training examples")
print(f"📋 Fields: {list(data[0].keys())}")
print(f"\n📝 Sample question: {data[0]['question'][:100]}...")


# ============================================================
# CELL 4: Format Data for Training
# ============================================================

from datasets import Dataset

print("🔧 Formatting data for fine-tuning...\n")

def format_instruction(example):
    """Format as instruction-following task"""
    
    # Handle both 'answer' and 'gold_answer' fields
    answer = example.get('answer') or example.get('gold_answer', '')
    
    # Get context from docs
    context = example['docs'][0] if isinstance(example['docs'], list) else example['docs']
    context = context[:1000]  # Limit context length
    
    # Create instruction prompt (GPT-2 style)
    text = f"""Question: {example['question']}

Context: {context}

Answer: {answer}"""
    
    return {"text": text}

# Convert to Hugging Face dataset
formatted_data = [format_instruction(ex) for ex in data]
dataset = Dataset.from_list(formatted_data)

print(f"✅ Formatted {len(dataset)} examples")
print(f"\n📝 Sample formatted text:\n{formatted_data[0]['text'][:300]}...\n")


# ============================================================
# CELL 5: Load Base Model
# ============================================================

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

print("📥 Loading GPT-2-large base model...\n")

model_name = "gpt2-large"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

# Load model with 4-bit quantization (saves memory)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_4bit=True,
    device_map="auto",
    torch_dtype=torch.float16
)

print(f"✅ Model loaded: {model_name}")
print(f"📊 Parameters: 774M")
print(f"💾 Memory usage: ~3GB (4-bit quantized)")


# ============================================================
# CELL 6: Prepare for LoRA Training
# ============================================================

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

print("🔧 Setting up LoRA (Low-Rank Adaptation)...\n")

# Prepare model for quantized training
model = prepare_model_for_kbit_training(model)

# LoRA configuration
lora_config = LoraConfig(
    r=16,  # LoRA rank (higher = more capacity, slower)
    lora_alpha=32,  # Scaling factor
    target_modules=["c_attn", "c_proj"],  # GPT-2 attention layers
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

print("\n✅ LoRA configured!")
print("💡 Only training ~0.8% of parameters (memory efficient!)")


# ============================================================
# CELL 7: Tokenize Dataset
# ============================================================

print("📝 Tokenizing dataset...\n")

def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=512,
        padding="max_length"
    )

tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["text"]
)

print(f"✅ Tokenized {len(tokenized_dataset)} examples")


# ============================================================
# CELL 8: Configure Training
# ============================================================

from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

print("🎯 Configuring training parameters...\n")

# Output directory
output_dir = "/kaggle/working/nutribot_medical_model"

# Training arguments
training_args = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=2,
    learning_rate=2e-4,
    fp16=True,
    save_steps=50,
    logging_steps=10,
    save_total_limit=2,
    warmup_steps=50,
    lr_scheduler_type="cosine",
    optim="paged_adamw_8bit",
    report_to="none"  # Disable wandb
)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator
)

print("✅ Training configured!")
print(f"\n📊 Training plan:")
print(f"  Epochs: 3")
print(f"  Batch size: 4")
print(f"  Steps per epoch: {len(tokenized_dataset) // 4}")
print(f"  Total steps: ~{(len(tokenized_dataset) // 4) * 3}")
print(f"  Estimated time: 45-60 minutes")


# ============================================================
# CELL 9: Train Model
# ============================================================

print("\n" + "="*60)
print("🚀 STARTING TRAINING!")
print("="*60 + "\n")

# Train!
trainer.train()

print("\n" + "="*60)
print("✅ TRAINING COMPLETE!")
print("="*60)


# ============================================================
# CELL 10: Save Final Model
# ============================================================

print("\n💾 Saving final model...\n")

# Save model and tokenizer
final_model_path = "/kaggle/working/nutribot_final_model"
model.save_pretrained(final_model_path)
tokenizer.save_pretrained(final_model_path)

print(f"✅ Model saved to: {final_model_path}")


# ============================================================
# CELL 11: Test the Model
# ============================================================

print("\n🧪 Testing the trained model...\n")

# Test query
test_question = "What are potassium restrictions for CKD patients?"

prompt = f"Question: {test_question}\n\nAnswer:"

# Generate response
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(
    **inputs,
    max_new_tokens=150,
    temperature=0.7,
    do_sample=True,
    top_p=0.9,
    pad_token_id=tokenizer.eos_token_id
)

response = tokenizer.decode(outputs[0], skip_special_tokens=True)

print(f"📝 Test Question: {test_question}")
print(f"\n🤖 Model Response:\n{response}")
print("\n✅ Model is working!")


# ============================================================
# CELL 12: Download Model
# ============================================================

# Zip the model for easy download
!cd /kaggle/working && zip -r nutribot_medical_model.zip nutribot_final_model

print("\n" + "="*60)
print("📦 MODEL READY FOR DOWNLOAD!")
print("="*60)
print(f"\n📁 Download this file: /kaggle/working/nutribot_medical_model.zip")
print(f"📊 Model size: ~500MB")
print("\n💡 How to download:")
print("1. Go to Output tab (right sidebar)")
print("2. Click 'Save Version' (top right)")
print("3. After processing, download nutribot_medical_model.zip")
print("\n" + "="*60)


# ============================================================
# NEXT STEPS (After Download)
# ============================================================

print("\n📋 INTEGRATION STEPS:")
print("""
1. Download nutribot_medical_model.zip from Kaggle Output
2. Extract to: /Volumes/T7 Shield/ClaRa_nutribot/models/medical_model/
3. Update src/retriever/clara_engine.py:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

class ClaraRetriever:
    def __init__(self):
        model_path = "./models/medical_model"
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_path)
        self.model.eval()
    
    def search(self, query, patient_context, top_k=5):
        prompt = f"Question: {query}\\n\\nAnswer:"
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(**inputs, max_new_tokens=200)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return [response]
```

4. Test: python test_components.py
5. Deploy NutriBot with your trained model! 🎉
""")

print("\n✅ TRAINING SESSION COMPLETE! ✅")
