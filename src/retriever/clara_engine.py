"""
Trained Medical Nutrition Model Retriever

Uses LoRA fine-tuned GPT-2-large model trained on medical nutrition PDFs.
Falls back to mock retriever if model files are not available.
"""

from pathlib import Path
from typing import List
from loguru import logger

class ClaraRetriever:
    """
    Medical Nutrition Model Retriever
    
    Loads trained LoRA model if available, otherwise uses mock retrieval.
    """
    
    def __init__(self):
        """Initialize retriever with trained model or fallback"""
        self.model_path = Path("/Volumes/T7 Shield/ClaRa_nutribot/models/nutribot_final_model")
        self.use_trained_model = False
        self.model = None
        self.tokenizer = None
        
        # Try to load trained model
        if self._check_model_exists():
            try:
                self._load_trained_model()
                self.use_trained_model = True
                logger.success("✅ Loaded trained medical nutrition model")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load trained model: {e}")
                logger.info("📋 Falling back to mock retriever")
                self._init_mock_retriever()
        else:
            logger.info("📋 Trained model not found - using mock retriever")
            self._init_mock_retriever()
    
    def _check_model_exists(self) -> bool:
        """Check if model files exist"""
        if not self.model_path.exists():
            return False
        
        required_files = ["adapter_config.json", "tokenizer_config.json"]
        return all((self.model_path / f).exists() for f in required_files)
    
    def _load_trained_model(self):
        """Load the trained LoRA model"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import AutoPeftModelForCausalLM
            
            logger.info("📥 Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            
            logger.info("📥 Loading LoRA model...")
            # Load PEFT model with adapter
            self.model = AutoPeftModelForCausalLM.from_pretrained(
                str(self.model_path),
                device_map="auto",
                low_cpu_mem_usage=True
            )
            self.model.eval()
            
        except ImportError:
            logger.warning("⚠️ transformers or peft not installed")
            raise
        except Exception as e:
            logger.error(f"❌ Model loading failed: {e}")
            raise
    
    def _init_mock_retriever(self):
        """Initialize simple mock knowledge base"""
        self.mock_kb = [
            "For CKD patients, limit potassium to 2000mg/day. Avoid bananas, spinach, and avocados.",
            "Warfarin patients should maintain consistent vitamin K intake. Limit leafy greens.",
            "Diabetes patients should focus on low glycemic index foods and complex carbohydrates.",
            "Hypertension patients should limit sodium to 1500mg/day. Avoid processed foods.",
            "Low potassium fruits include apples (195mg), berries, and grapes - safe for CKD.",
        ]
    
    def search(self, query: str, patient_context: str, top_k: int = 5) -> List[str]:
        """
        Search for nutrition information
        
        Args:
            query: User's question
            patient_context: Patient health information
            top_k: Number of results
        
        Returns:
            List of nutrition recommendations
        """
        if self.use_trained_model:
            return self._search_with_model(query, patient_context, top_k)
        else:
            return self._search_mock(query, top_k)
    
    def _search_with_model(self, query: str, patient_context: str, top_k: int) -> List[str]:
        """Search using trained model"""
        try:
            # Create prompt
            prompt = f"""Question: {query}

Context: {patient_context[:500]}

Answer:"""
            
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            
            # Generate
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Decode
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract just the answer part
            if "Answer:" in response:
                answer = response.split("Answer:")[-1].strip()
            else:
                answer = response
            
            logger.info(f"🤖 Generated response: {answer[:100]}...")
            return [answer]
            
        except Exception as e:
            logger.error(f"❌ Model inference failed: {e}")
            logger.info("📋 Falling back to mock retriever")
            return self._search_mock(query, top_k)
    
    def _search_mock(self, query: str, top_k: int) -> List[str]:
        """Simple keyword-based mock search"""
        query_lower = query.lower()
        results = []
        
        for fact in self.mock_kb:
            # Simple keyword matching
            if any(word in fact.lower() for word in query_lower.split()):
                results.append(fact)
        
        return results[:top_k] if results else self.mock_kb[:top_k]