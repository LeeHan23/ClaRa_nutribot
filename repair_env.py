import sys
import subprocess
import os

def install(package):
    print(f"📦 Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")

def uninstall(package):
    print(f"🗑️ Uninstalling {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", package])
        print(f"✅ Successfully uninstalled {package}")
    except subprocess.CalledProcessError:
        print(f"⚠️ Could not uninstall {package} (maybe not installed)")

if __name__ == "__main__":
    print("🔧 Repairing Python Environment...")
    print(f"🐍 Python: {sys.executable}")
    
    # 1. Uninstall potentially corrupted packages
    uninstall("transformers")
    uninstall("peft")
    
    # 2. Install known working versions
    install("transformers==4.36.0")
    install("peft==0.6.0")
    install("accelerate")
    install("bitsandbytes")
    
    # 3. Verify
    try:
        import transformers
        import peft
        print("\n✅ Verification Successful!")
        print(f"Transformers: {transformers.__version__}")
        print(f"PEFT: {peft.__version__}")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
