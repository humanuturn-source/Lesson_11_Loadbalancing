import os
import sys
import logging
import json
import re
import time
from typing import Dict, Any, List, Optional
import ollama

from mcp_servers import query_inventory, search_return_policy, get_store_hours

# ==========================================
# LOGGING CONFIGURATION
# ==========================================
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(message)s"))

root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("MCP_MultiAgent")


# ==========================================
# MCP CLIENT INTERFACE WRAPPER
# ==========================================
class MCPClientRegistry:
    def __init__(self):
        self.tools = {
            "query_inventory": query_inventory,
            "search_return_policy": search_return_policy,
            "get_store_hours": get_store_hours
        }

    def execute_mcp_tool(self, tool_name: str, **kwargs) -> str:
        logger.info(f"[MCP CLIENT] Executing tool '{tool_name}' with args: {kwargs}")
        if tool_name in self.tools:
            try:
                result = self.tools[tool_name](**kwargs)
                return str(result)
            except Exception as e:
                logger.error(f"[MCP TOOL ERROR] {tool_name} failed: {str(e)}")
                return f"MCP Tool execution error: {str(e)}"
        return f"Tool '{tool_name}' not found."


# ==========================================
# AGENT SYSTEM WITH DYNAMIC MODEL ROUTING
# ==========================================
class MCPSupermarketHelpDesk:
    def __init__(
        self, 
        reasoning_model: str = "gemma4", 
        fast_model: str = "gemma:2b"
    ):
        """
        :param reasoning_model: High-parameter model for complex synthesis, vision tasks, and final user replies.
        :param fast_model: Ultra-fast lightweight SLM for routing, intent analysis, and structured JSON parsing.
        """
        self.reasoning_model = reasoning_model
        self.fast_model = fast_model
        self.mcp_client = MCPClientRegistry()

    def _call_llm(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        image_path: Optional[str] = None, 
        tier: str = "reasoning"
    ) -> str:
        """Dynamically routes queries to designated local model tier with execution latency logging."""
        target_model = self.reasoning_model if (image_path or tier == "reasoning") else self.fast_model
        start_time = time.time()

        try:
            message_payload = {"role": "user", "content": f"System Task: {system_prompt}\nUser Query: {user_prompt}"}
            
            if image_path and os.path.exists(image_path):
                message_payload["images"] = [image_path]

            response = ollama.chat(
                model=target_model,
                messages=[message_payload]
            )
            elapsed = time.time() - start_time
            content = response["message"]["content"].strip()
            logger.info(f"[ROUTER METRICS] Tier: '{tier}' | Model: '{target_model}' | Latency: {elapsed:.2f}s")
            return content

        except Exception as e:
            logger.error(f"Ollama execution error on model '{target_model}': {str(e)}")
            # Fallback strategy: If reasoning model fails or OOMs, attempt fast model fallback
            if tier == "reasoning":
                logger.warning(f"[FAILOVER TRIGGERED] Falling back to fast model '{self.fast_model}'...")
                return self._call_llm(system_prompt, user_prompt, image_path=None, tier="fast")
            return f"Error executing local model ({target_model}): {str(e)}"

    def agent_intent_router(self, query: str, image_path: Optional[str] = None) -> str:
        logger.info(f"-> AGENT 1 [Dynamic Router]: Evaluating task intent (Image Attached: {image_path is not None})...")
        if image_path:
            return "VISION_TASK"

        system_prompt = (
            "You are an Intent Classification Agent.\n"
            "Categorize the user query into EXACTLY ONE keyword:\n"
            "- PRODUCT: Inventory, stock availability, search, price.\n"
            "- RETURN_POLICY: Returns, refunds, policy rules, receipts.\n"
            "- WORKING_HOURS: Store opening hours, holiday schedule.\n"
            "- GENERAL: Greetings, simple general inquiries.\n\n"
            "Return ONLY the category keyword."
        )
        # Execute low-complexity routing via ultra-fast model tier
        intent = self._call_llm(system_prompt, query, tier="fast").upper()
        
        for valid in ["PRODUCT", "RETURN_POLICY", "WORKING_HOURS", "GENERAL"]:
            if valid in intent:
                return valid
        return "GENERAL"

    def agent_vision_specialist(self, query: str, image_path: str) -> str:
        logger.info(f"-> AGENT 5 [Vision Specialist]: Processing visual image via {self.reasoning_model}...")
        
        # 1. Comprehensive Vision Prompt (Handles both Product Photos & Store Receipts)
        vision_prompt = (
            "You are a Supermarket Visual Assistant.\n"
            "Analyze the image and extract the following based on image type:\n\n"
            "IF THE IMAGE IS A RECEIPT:\n"
            "- Item Description / Purchased Items\n"
            "- Purchase Date (YYYY-MM-DD format)\n"
            "- Total Price\n"
            "- Store Name\n\n"
            "IF THE IMAGE IS A PRODUCT/FRUIT PHOTO:\n"
            "- Item Name / Description\n"
            "- Quantity / Packaging (if visible)\n\n"
            "Provide a concise summary of what is visible in the image."
        )
        visual_analysis = self._call_llm(vision_prompt, query, image_path=image_path, tier="reasoning")
        logger.info(f"[VISION ANALYSIS RESULT]:\n{visual_analysis}")

        # 2. Extract structured metadata on fast SLM tier
        extract_prompt = (
            "Extract structured info from the text and return ONLY valid raw JSON (no code blocks) with keys:\n"
            '{"item_name": "string", "purchase_date": "YYYY-MM-DD or null", "intent": "RETURN or INVENTORY"}'
        )
        json_str = self._call_llm(extract_prompt, visual_analysis, tier="fast")
        
        try:
            cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_json)
        except Exception:
            data = {"item_name": "Item", "purchase_date": None, "intent": "RETURN" if "return" in query.lower() else "INVENTORY"}

        item_name = data.get("item_name", "Item")
        purchase_date = data.get("purchase_date")
        intent = data.get("intent", "INVENTORY")

        # 3. Call corresponding MCP tool
        if intent == "RETURN" or "return" in query.lower():
            if not purchase_date or purchase_date == "null":
                mcp_data = "Receipt error: Purchase date missing or unreadable on the receipt. Unable to calculate return eligibility."
            else:
                mcp_data = self.mcp_client.execute_mcp_tool("search_return_policy", item_name=item_name, purchase_date_str=purchase_date)
        else:
            mcp_data = self.mcp_client.execute_mcp_tool("query_inventory", item_name=item_name)

        # 4. Strictly Grounded Final Synthesis Prompt
        final_prompt = (
            "You are a Supermarket Help Desk Agent.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Answer user queries strictly using the MCP Verification Data provided below.\n"
            "2. For inventory checks: If MCP Verification indicates no product was found, state clearly that the item is NOT available or out of stock.\n"
            "3. For returns: Rely on the policy verification result to state return eligibility.\n"
            "4. NEVER claim the store carries an item if the database verification returned no matching results.\n\n"
            f"Visual Extract: {visual_analysis}\n"
            f"MCP Verification Data: {mcp_data}"
        )
        return self._call_llm(final_prompt, query, tier="reasoning")



    def agent_product_specialist(self, query: str) -> str:
        logger.info("-> AGENT 2 [Product Specialist]: Processing inventory inquiry...")
        
        # 1. Enforce Structured JSON Extraction
        extract_prompt = (
            "Extract the main product entity from the user query.\n"
            "Respond ONLY in valid raw JSON with no Markdown formatting or extra text.\n"
            'Format: {"product_name": "apples"}'
        )
        raw_output = self._call_llm(extract_prompt, query, tier="fast")
        
        # 2. Parse JSON Payload safely with fallback
        keyword = ""
        try:
            cleaned = raw_output.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            keyword = data.get("product_name", "").strip()
        except Exception:
            # Fallback if JSON parsing fails: strip punctuation/quotes
            keyword = re.sub(r'[^\w\s]', '', raw_output).strip()

        # Sanity check: If extracted keyword is invalid/generic, extract common nouns directly from query
        if not keyword or keyword.lower() in ["in stock", "stock", "item", "product"]:
            # Simple fallback to grab words before 'in stock' or from the prompt directly
            match = re.search(r'([\w\s]+?)\s+(?:in stock|price|available)', query, re.IGNORECASE)
            keyword = match.group(1).strip() if match else query

        logger.info(f"[CLEANED KEYWORD]: '{keyword}'")
        
        mcp_data = self.mcp_client.execute_mcp_tool("query_inventory", item_name=keyword)
        
        # Synthesis on reasoning tier
        system_prompt = (
            "You are an Inventory Assistant.\n"
            "Answer using ONLY the following inventory tool data:\n"
            f"{mcp_data}"
        )
        return self._call_llm(system_prompt, query, tier="reasoning")




    def agent_policy_specialist(self, query: str) -> str:
        logger.info("-> AGENT 3 [Policy Specialist]: Checking policy details...")
        mcp_data = self.mcp_client.execute_mcp_tool("search_return_policy", item_name="Milk", purchase_date_str="2026-09-25")
        
        system_prompt = (
            "You are a Store Policy Specialist.\n"
            "Answer the customer using this policy verification data:\n"
            f"{mcp_data}"
        )
        return self._call_llm(system_prompt, query, tier="reasoning")

    def agent_schedule_specialist(self, query: str) -> str:
        logger.info("-> AGENT 4 [Schedule Specialist]: Checking store hours...")
        mcp_data = self.mcp_client.execute_mcp_tool("get_store_hours", day_or_holiday=query)
        
        system_prompt = (
            "You are a Customer Operations Assistant.\n"
            "Answer using the real-time schedule information below:\n"
            f"{mcp_data}"
        )
        return self._call_llm(system_prompt, query, tier="reasoning")

    def process_query(self, user_query: str, image_path: Optional[str] = None) -> str:
        logger.info("=" * 70)
        logger.info(f"USER QUERY: \"{user_query}\" | IMAGE: {image_path}")
        logger.info("=" * 70)

        intent = self.agent_intent_router(user_query, image_path=image_path)

        if intent == "VISION_TASK":
            return self.agent_vision_specialist(user_query, image_path)
        elif intent == "PRODUCT":
            return self.agent_product_specialist(user_query)
        elif intent == "RETURN_POLICY":
            return self.agent_policy_specialist(user_query)
        elif intent == "WORKING_HOURS":
            return self.agent_schedule_specialist(user_query)
        else:
            return self._call_llm("You are a friendly supermarket customer assistant.", user_query, tier="fast")


if __name__ == "__main__":
    help_desk = MCPSupermarketHelpDesk(
        reasoning_model="gemma4", 
        fast_model="gemma:2b"
    )
    
    # Test execution
    sample_query = "Do you have any organic apples in stock and how much are they?"
    response = help_desk.process_query(sample_query)
    print("\n--- FINAL RESPONSE ---")
    print(response)
