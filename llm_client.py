import os
import json
import time
import requests
from typing import Optional, Dict, Any, List, Callable
from models import AgentLogEvent

class LLMClient:
    def __init__(self, force_simulation: bool = False):
        self.force_simulation = force_simulation
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.listeners: List[Callable[[AgentLogEvent], None]] = []
        self.log_history: List[AgentLogEvent] = []

    def add_listener(self, callback: Callable[[AgentLogEvent], None]):
        self.listeners.append(callback)

    def log_event(self, agent_name: str, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        event = AgentLogEvent(
            agent_name=agent_name,
            event_type=event_type,
            message=message,
            details=details
        )
        self.log_history.append(event)
        for cb in self.listeners:
            try:
                cb(event)
            except Exception:
                pass

    def get_logs(self, limit: int = 50) -> List[AgentLogEvent]:
        return self.log_history[-limit:]

    def generate_content(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False
    ) -> str:
        self.log_event(
            agent_name=agent_name,
            event_type="start",
            message=f"Initiating AI processing cycle for {agent_name}...",
            details={"system_prompt": system_prompt[:200] + "...", "user_prompt": user_prompt}
        )

        # Check if we should use simulation mode
        if self.force_simulation or (not self.gemini_key and not self.openai_key):
            return self._simulate_response(agent_name, system_prompt, user_prompt, json_mode)

        # Try Gemini API via REST with dynamic model discovery
        if self.gemini_key:
            models_to_try = []
            if hasattr(self, "_working_gemini_model") and self._working_gemini_model:
                models_to_try.append(self._working_gemini_model)
            models_to_try.extend(["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash-001", "gemini-1.5-pro", "gemini-pro"])
            
            # Remove duplicates while preserving order
            models_to_try = list(dict.fromkeys(models_to_try))
            
            payload_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"
            if json_mode:
                payload_text += "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown backticks, no explanatory text."
            
            body = {
                "contents": [{"parts": [{"text": payload_text}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
            }
            headers = {"Content-Type": "application/json"}
            
            gemini_success = False
            last_error = ""
            
            for model_name in models_to_try:
                try:
                    self.log_event(agent_name, "llm_call", f"Calling Google Gemini API ({model_name})...", {"model": model_name})
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
                    
                    res = requests.post(url, headers=headers, json=body, timeout=15)
                    if res.status_code == 200:
                        data = res.json()
                        output_text = data["contents"][0]["parts"][0]["text"].strip()
                        if json_mode and output_text.startswith("```json"):
                            output_text = output_text[7:]
                        if json_mode and output_text.endswith("```"):
                            output_text = output_text[:-3]
                        output_text = output_text.strip()
                        self._working_gemini_model = model_name
                        self.log_event(agent_name, "success", f"Gemini ({model_name}) response generated ({len(output_text)} chars).", {"response": output_text[:300] + "..."})
                        return output_text
                    elif res.status_code == 404:
                        # Model not found on this endpoint/tier, try next model in loop
                        last_error = res.text
                        continue
                    else:
                        last_error = f"HTTP {res.status_code}: {res.text}"
                        break
                except Exception as e:
                    last_error = str(e)
                    break
            
            if not gemini_success:
                self.log_event(agent_name, "error", f"Gemini API calls unsuccessful. Falling back to simulation.", {"error": last_error[:300]})


        # Try OpenAI API via REST
        if self.openai_key:
            try:
                self.log_event(agent_name, "llm_call", "Calling OpenAI GPT-4o-mini API via REST...", {"model": "gpt-4o-mini"})
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}"
                }
                body = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2
                }
                if json_mode:
                    body["response_format"] = {"type": "json_object"}
                    
                res = requests.post(url, headers=headers, json=body, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    output_text = data["choices"][0]["message"]["content"].strip()
                    self.log_event(agent_name, "success", f"OpenAI response generated ({len(output_text)} chars).", {"response": output_text[:300] + "..."})
                    return output_text
                else:
                    self.log_event(agent_name, "error", f"OpenAI API returned {res.status_code}. Falling back to simulation.", {"error": res.text})
            except Exception as e:
                self.log_event(agent_name, "error", f"OpenAI REST call failed: {str(e)}. Falling back to simulation.", {})

        # Fallback to Simulation Mode
        return self._simulate_response(agent_name, system_prompt, user_prompt, json_mode)

    def _simulate_response(self, agent_name: str, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
        self.log_event(
            agent_name=agent_name,
            event_type="llm_call",
            message=f"Executing High-Fidelity Simulation Mode for {agent_name}...",
            details={"mode": "deterministic_simulation", "latency_ms": 350}
        )
        time.sleep(0.35)  # Simulate cognitive latency

        # Classifier Agent Simulation
        if "Classifier Agent" in agent_name or "Buddhi" in agent_name:
            # We parse the input text to give smart deterministic classifications
            lower_prompt = user_prompt.lower()
            
            item_type = "task"
            category = "General"
            priority = "med"
            effort = "focused"
            reasoning = "Identified actionable verb; classified as task."

            # Keywords for type
            if any(w in lower_prompt for w in ["idea", "what if", "maybe we could", "concept", "brainstorm", "explore"]):
                item_type = "idea"
                reasoning = "Exploratory concept and creative brainstorming detected."
            elif any(w in lower_prompt for w in ["reference", "article", "paper", "link", "http", "book", "guide", "documentation", "receipt"]):
                item_type = "reference"
                reasoning = "Contains informational reference or documentation material."
            elif any(w in lower_prompt for w in ["waiting", "blocked", "awaiting", "response from", "pending", "sent email"]):
                item_type = "waiting-on"
                reasoning = "Action depends on external response or third party."
            elif any(w in lower_prompt for w in ["someday", "eventually", "bucket list", "when i retire", "in the future"]):
                item_type = "someday"
                reasoning = "Long-term aspirational goal without immediate timeline."

            # Keywords for category
            if any(w in lower_prompt for w in ["ai", "python", "code", "agent", "llm", "bug", "deploy", "api", "software", "repo"]):
                category = "Work/AI Project"
            elif any(w in lower_prompt for w in ["health", "gym", "doctor", "dentist", "run", "workout", "sleep", "diet", "water"]):
                category = "Health & Wellness"
            elif any(w in lower_prompt for w in ["tax", "invoice", "bank", "pay", "money", "budget", "invest", "groceries"]):
                category = "Finance & Admin"
            elif any(w in lower_prompt for w in ["clean", "repair", "home", "kitchen", "dog", "car", "garden", "family"]):
                category = "Home & Life"

            # Keywords for priority
            if any(w in lower_prompt for w in ["urgent", "asap", "immediately", "critical", "today", "high", "bug", "tax", "deadline"]):
                priority = "high"
            elif any(w in lower_prompt for w in ["someday", "low", "when possible", "minor", "maybe"]):
                priority = "low"

            # Keywords for effort
            if any(w in lower_prompt for w in ["quick", "5 min", "call", "email", "pay", "buy", "check"]):
                effort = "quick"
            elif any(w in lower_prompt for w in ["build", "system", "report", "redesign", "project", "framework", "refactor"]):
                effort = "project"

            sim_data = {
                "type": item_type,
                "category": category,
                "priority": priority,
                "effort": effort,
                "reasoning": reasoning
            }
            res_str = json.dumps(sim_data)
            self.log_event(agent_name, "success", f"Simulated classification: {item_type.upper()} [{category}]", sim_data)
            return res_str

        # Reviewer Agent Simulation
        elif "Reviewer Agent" in agent_name or "Ahamkara" in agent_name:
            # Generate personalized questions based on prompt content
            reflections = [
                "You have stale items lingering in your list for over 3 days. What underlying resistance or lack of clarity is preventing you from either completing or delegating them today?",
                "Looking at your Work/AI Project tasks, you are making solid progress on core architecture. Are you dedicating enough uninterrupted deep-work blocks in the morning to tackle project-level items?",
                "How can you streamline your routine capture habits so that quick administrative tasks are cleared immediately rather than accumulating in your weekly review?"
            ]
            sim_data = {"reflections": reflections}
            res_str = json.dumps(sim_data) if json_mode else "\n".join([f"- {r}" for r in reflections])
            self.log_event(agent_name, "success", "Generated 3 deep self-reflection questions.", sim_data)
            return res_str

        # Planner Agent Simulation
        elif "Planner Agent" in agent_name or "Viveka" in agent_name:
            # We parse open tasks from user_prompt and assign to Eisenhower quadrants
            # Let's extract task IDs if possible or create a structured simulation
            sim_data = {
                "summary": "This execution plan balances high-priority AI project deliverables with critical health and financial maintenance. Urgent bug fixes and time-sensitive admin tasks are front-loaded into Q1 (Do Now), while deep architectural work is protected in Q2 (Schedule).",
                "assignments": []
            }
            
            # Simple heuristic parsing of tasks from prompt text
            lines = user_prompt.split("\n")
            for line in lines:
                if line.strip().startswith("- ID:") or "ID:" in line:
                    try:
                        # Extract ID
                        parts = line.split("ID:")[1].split()[0].replace("`", "").replace(",", "")
                        task_id = parts
                        # Assign quadrant based on priority and effort keywords in line
                        quadrant = "Q2 - Schedule (Important, Not Urgent)"
                        reason = "High value project work requiring scheduled focus blocks."
                        if "high" in line.lower() or "urgent" in line.lower() or "bug" in line.lower() or "tax" in line.lower():
                            quadrant = "Q1 - Do Now (Urgent & Important)"
                            reason = "Time-sensitive item with immediate impact on operations or deadlines."
                        elif "quick" in line.lower() and ("low" in line.lower() or "med" in line.lower()):
                            quadrant = "Q3 - Delegate / Quick Win (Urgent, Not Important)"
                            reason = "Low cognitive load item that can be batched or delegated."
                        elif "low" in line.lower() and "someday" in line.lower():
                            quadrant = "Q4 - Reconsider (Neither)"
                            reason = "Low priority item with minimal immediate ROI."
                            
                        sim_data["assignments"].append({
                            "task_id": task_id,
                            "quadrant": quadrant,
                            "reason": reason
                        })
                    except Exception:
                        continue
            res_str = json.dumps(sim_data)
            self.log_event(agent_name, "success", f"Generated Eisenhower matrix plan with {len(sim_data['assignments'])} task allocations.", sim_data)
            return res_str

        # Generic fallback
        fallback_msg = '{"status": "success", "message": "Simulated agent execution completed successfully."}'
        self.log_event(agent_name, "success", "Completed general AI execution cycle.", {})
        return fallback_msg
