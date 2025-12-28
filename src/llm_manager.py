from typing import Dict, Optional, List
from logger import get_logger

logger = get_logger(__name__)

class LLMManager:
    """Manages LLM interactions via Ollama."""
    
    def __init__(self, model_name: str = "gemma3:4b"):
        """Initialize LLM manager."""
        self.model_name = model_name
        self.available = False
        
        try:
            import ollama
            self.client = ollama.Client()
            # Test connection
            self._test_connection()
        except ImportError:
            logger.warning("Ollama not installed or not available. LLM features will be limited.")
            self.client = None
        except Exception as e:
            logger.warning(f"Ollama connection failed: {str(e)}. Using fallback reasoning.")
            self.client = None
    
    def _test_connection(self):
        """Test if Ollama is available."""
        try:
            # Try a quick model list call
            self.client.list()
            self.available = True
            logger.info(f"Ollama connected successfully. Model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Ollama test failed: {str(e)}")
            self.available = False
    
    def generate_reasoning(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """Generate LLM reasoning about a document."""
        
        if not self.available or not self.client:
            logger.debug("LLM not available, using fallback reasoning")
            return None
        
        try:
            logger.debug(f"Generating reasoning via {self.model_name}")
            
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                temperature=temperature,
                num_predict=max_tokens,
                stream=False
            )
            
            if response:
                reasoning = response.get("response", "").strip()
                logger.debug(f"Generated reasoning: {reasoning[:100]}...")
                return reasoning
            
            return None
        
        except Exception as e:
            logger.warning(f"Error generating reasoning: {str(e)}")
            return None
    
    def classify_with_reasoning(
        self,
        vendor_name: str,
        description: str,
        similar_examples: List[str],
        confidence: float
    ) -> Dict:
        """Use LLM to improve classification when confidence is low."""
        
        if not self.available:
            return {"improved": False, "reasoning": None}
        
        # Build prompt
        prompt = f"""You are an accounting expert. Analyze this vendor and classify them to an expense category.

Vendor Name: {vendor_name}
Description: {description}
Current Confidence: {confidence:.0%}

Similar invoices from database:
{chr(10).join(f"- {ex}" for ex in similar_examples[:3])}

Expense Categories:
- rent: Office/commercial space rental
- salary: Employee salary and wages
- professional: Professional services, consulting
- contract: Contract work, catering, supply contracts
- utilities: Electricity, water, internet
- office_supplies: Stationery, office equipment
- travel: Travel and transportation
- maintenance: Maintenance and repairs
- other_expenses: Miscellaneous

Based on the vendor name, description, and similar examples, which category is most appropriate?
Respond with ONLY the category name and brief reasoning (1-2 sentences)."""
        
        reasoning = self.generate_reasoning(prompt, max_tokens=200)
        
        if not reasoning:
            return {"improved": False, "reasoning": None}
        
        # Parse response to extract category
        reasoning_lower = reasoning.lower()
        categories = [
            "rent", "salary", "professional", "contract", "utilities",
            "office_supplies", "travel", "maintenance", "other_expenses"
        ]
        
        selected_category = None
        for cat in categories:
            if cat in reasoning_lower:
                selected_category = cat
                break
        
        return {
            "improved": selected_category is not None,
            "reasoning": reasoning,
            "suggested_category": selected_category
        }
    
    def validate_extraction(
        self,
        raw_text: str,
        extracted_fields: Dict
    ) -> Dict:
        """Use LLM to validate extracted fields against raw text."""
        
        if not self.available:
            return {"validation_passed": True, "feedback": None}
        
        # Build validation prompt
        fields_str = "\n".join(
            f"- {k}: {v}" for k, v in extracted_fields.items() if v
        )
        
        prompt = f"""Review this invoice data extraction for accuracy.

Raw text excerpt:
{raw_text[:500]}

Extracted fields:
{fields_str}

Are these fields correctly extracted? Identify any errors or missing important information.
Respond with ONLY: VALID or list issues (one per line)."""
        
        validation = self.generate_reasoning(prompt, max_tokens=200)
        
        if not validation:
            return {"validation_passed": True, "feedback": None}
        
        is_valid = "valid" in validation.lower() and "error" not in validation.lower()
        
        return {
            "validation_passed": is_valid,
            "feedback": validation
        }
