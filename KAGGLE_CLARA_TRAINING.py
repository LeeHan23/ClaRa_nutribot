# ============================================================
# KAGGLE CLARA TRAINING NOTEBOOK
# Complete CLaRa Stage 1 Training for Medical Nutrition Model
# ============================================================
# 
# INSTRUCTIONS:
# 1. Go to https://www.kaggle.com
# 2. Create New Notebook
# 3. Enable GPU: Settings → Accelerator → GPU T4 x2
# 4. Copy this entire file into Kaggle cells (split by # CELL markers)
# 5. Upload your nutrition_train.jsonl to Kaggle Input
# 6. Run all cells sequentially
#
# Expected time: 3-4 hours on Kaggle GPU
# ============================================================

# ============================================================
# CELL 1: Verify GPU
# ============================================================

import torch

print("🔍 Checking GPU availability...\n")

if torch.cuda.is_available():
    print(f"✅ GPU Detected: {torch.cuda.get_device_name(0)}")
    print(f"✅ CUDA Version: {torch.version.cuda}")
    print(f"✅ Device Count: {torch.cuda.device_count()}")
    print("\n🎉 GPU is ready! Proceed to next cell.")
else:
    print("❌ No GPU detected!")
    print("⚠️ Go to Settings → Accelerator → Select GPU T4 x2")
    print("⚠️ Then restart and re-run this cell")


# ============================================================
# CELL 2: Install Dependencies
# ============================================================

import sys, os

print("🔧 Installing CLaRa dependencies...\n")

# Uninstall conflicts
!pip uninstall -y transformers peft accelerate deepspeed -q

# Install PyTorch 2.1.0 (compatible with DeepSpeed)
print("📦 Installing PyTorch 2.1.0...")
!pip install -q torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu118

# Install compatible versions
print("📦 Installing transformers, peft, accelerate...")
!pip install -q transformers==4.35.2 peft==0.6.0 accelerate==0.24.1 datasets==2.14.6

# Install DeepSpeed
print("📦 Installing DeepSpeed 0.12.3...")
!pip install -q deepspeed==0.12.3

# Other dependencies
print("📦 Installing other dependencies...")
!pip install -q sentencepiece einops bitsandbytes tensorboard

# Install OpenRLHF
print("📦 Installing OpenRLHF...")
!rm -rf /kaggle/working/OpenRLHF
!git clone -q https://github.com/OpenLLMAI/OpenRLHF.git /kaggle/working/OpenRLHF
os.chdir('/kaggle/working/OpenRLHF')
!pip install -q -e .

# Clone ml-clara
print("📦 Cloning ml-clara...")
os.chdir('/kaggle/working')
!rm -rf ml-clara
!git clone -q https://github.com/apple/ml-clara.git
os.chdir('/kaggle/working/ml-clara')

# Verify
print("\n" + "="*60)
print("🧪 Verifying installation...")
print("="*60 + "\n")

import torch
print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ CUDA: {torch.cuda.is_available()}")

try:
    from openrlhf.datasets import SFTDataset
    print(f"✅ OpenRLHF imported")
except Exception as e:
    print(f"❌ OpenRLHF: {e}")

try:
    import deepspeed
    print(f"✅ DeepSpeed: {deepspeed.__version__}")
except Exception as e:
    print(f"❌ DeepSpeed: {e}")

print("\n✅ Installation complete!")


# ============================================================
# CELL 3: Upload Your Training Data
# ============================================================

# INSTRUCTIONS:
# 1. Click "Add Data" on the right sidebar in Kaggle
# 2. Click "Upload" → Upload your nutrition_train.jsonl
# 3. The file will appear in /kaggle/input/
# 4. Update the path below if needed

import json
from pathlib import Path

# Update this path to match your uploaded file
DATA_PATH = "/kaggle/input/nutrition-train/nutrition_train.jsonl"  # Change if needed

# Verify file exists
if Path(DATA_PATH).exists():
    with open(DATA_PATH) as f:
        data = [json.loads(line) for line in f]
    print(f"✅ Loaded {len(data)} training examples")
    print(f"📋 Sample: {list(data[0].keys())}")
else:
    print(f"❌ File not found: {DATA_PATH}")
    print("⚠️ Upload nutrition_train.jsonl to Kaggle Input")
    print("⚠️ Then update DATA_PATH in this cell")


# ============================================================
# CELL 4: Prepare Data Directory
# ============================================================

import os

os.chdir('/kaggle/working/ml-clara')

# Create data directory
!mkdir -p data

# Copy training data
!cp {DATA_PATH} ./data/nutrition_train.jsonl

# Verify
!wc -l data/nutrition_train.jsonl

print("\n✅ Data ready for training!")


# ============================================================
# CELL 5: Fix Data Format for CLaRa
# ============================================================

import json

print("🔧 Checking data format...\n")

# Read data
with open("/kaggle/working/ml-clara/data/nutrition_train.jsonl") as f:
    data = [json.loads(line) for line in f]

print(f"📊 Loaded {len(data)} examples")
print(f"📋 Fields: {list(data[0].keys())}")

# Fix format if needed (handle both 'answer' and 'gold_answer')
fixed_data = []
for item in data:
    answer_field = item.get("answer") or item.get("gold_answer")
    
    if not answer_field:
        print(f"⚠️ Skipping item with no answer")
        continue
    
    fixed_item = {
        "question": item["question"],
        "docs": item["docs"],
        "answer": answer_field
    }
    fixed_data.append(fixed_item)

# Save
with open("/kaggle/working/ml-clara/data/nutrition_train.jsonl", "w") as f:
    for item in fixed_data:
        f.write(json.dumps(item) + "\n")

print(f"✅ Fixed {len(fixed_data)} examples")


# ============================================================
# CELL 6: Fix LoRA Config for GPT-2
# ============================================================

print("🔧 Patching modeling_clara.py...\n")

file_path = "/kaggle/working/ml-clara/openrlhf/models/modeling_clara.py"

# Read file
with open(file_path, 'r') as f:
    lines = f.readlines()

# Fix target_modules line
fixed_lines = []
for i, line in enumerate(lines):
    if 'target_modules' in line and ('all-linear' in line or '], "v_proj"' in line or '], "' in line):
        indent = len(line) - len(line.lstrip())
        fixed_line = ' ' * indent + 'target_modules=["q_proj", "v_proj", "dense", "fc1", "fc2"],\n'
        fixed_lines.append(fixed_line)
        print(f"✅ Fixed line {i+1}")
    else:
        fixed_lines.append(line)

# Write back
with open(file_path, 'w') as f:
    f.writelines(fixed_lines)

print("💾 File patched!")


# ============================================================
# CELL 7: Download GPT-2-large + Add Chat Template
# ============================================================

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

print("📥 Loading GPT-2-large...\n")

# Load model
model = AutoModelForCausalLM.from_pretrained(
    "gpt2-large",
    torch_dtype=torch.float16
)
tokenizer = AutoTokenizer.from_pretrained("gpt2-large")

# Add padding token
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = model.config.eos_token_id

# Add chat template
chat_template = """{% for message in messages %}{% if message['role'] == 'user' %}{{ 'User: ' + message['content'] + '\n' }}{% elif message['role'] == 'assistant' %}{{ 'Assistant: ' + message['content'] + '\n' }}{% endif %}{% endfor %}"""
tokenizer.chat_template = chat_template

# Save
local_path = "/kaggle/working/gpt2-large-with-template"
print(f"💾 Saving to {local_path}...")
model.save_pretrained(local_path)
tokenizer.save_pretrained(local_path)

print("✅ GPT-2-large ready!")


# ============================================================
# CELL 8: CLaRa Stage 1 Training
# ============================================================

import os
os.chdir('/kaggle/working/ml-clara')

print("🚀 Starting CLaRa Stage 1 Training!")
print("⏱️ Estimated time: 3-4 hours on Kaggle GPU\n")

# Set PYTHONPATH and run training
os.environ['PYTHONPATH'] = '/kaggle/working/ml-clara:' + os.environ.get('PYTHONPATH', '')

!python openrlhf/cli/train_sft.py \
    --pretrain /kaggle/working/gpt2-large-with-template \
    --dataset data/nutrition_train.jsonl \
    --dataset_probs 1.0 \
    --train_batch_size 2 \
    --micro_train_batch_size 1 \
    --max_len 512 \
    --max_epochs 3 \
    --learning_rate 2e-4 \
    --save_path /kaggle/working/nutribot_clara_stage1 \
    --save_steps 50 \
    --logging_steps 10 \
    --compress_rate 32 \
    --doc_max_length 256 \
    --gradient_checkpointing \
    --bf16 \
    --zero_stage 2

print("\n✅ CLaRa Stage 1 complete!")


# ============================================================
# CELL 9: Download Trained Model
# ============================================================

# OPTION 1: Download directly from Kaggle
print("📦 Trained model saved to: /kaggle/working/nutribot_clara_stage1")
print("\n💡 To download:")
print("1. Go to Output tab on the right")
print("2. Click 'Save Version' (top right)")
print("3. After version completes, download nutribot_clara_stage1 folder")

# OPTION 2: Zip and download
!cd /kaggle/working && zip -r nutribot_clara_stage1.zip nutribot_clara_stage1

print("\n✅ Zipped model: /kaggle/working/nutribot_clara_stage1.zip")
print("Download this file from the Output tab!")


# ============================================================
# END OF KAGGLE NOTEBOOK
# ============================================================
# 
# NEXT STEPS:
# 1. Download the trained model (nutribot_clara_stage1.zip)
# 2. Extract it to /Volumes/T7 Shield/ClaRa_nutribot/models/clara_trained/
# 3. Update src/retriever/clara_engine.py to load the model
# 4. Test with: python test_components.py
#
# The trained model will replace your mock retriever with real
# CLaRa-compressed medical nutrition knowledge!
# ============================================================
