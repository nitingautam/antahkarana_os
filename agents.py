import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from models import (
    InboxItem, ClassifiedItem, TaskItem, NoteItem, ArchiveItem,
    ReviewDigest, PlanDigest, EisenhowerItem, ItemType, Priority, Effort
)
from storage import StorageManager
from llm_client import LLMClient


class CaptureAgent:
    """Manas — Sensory Capture: Appends unstructured notes or files to inbox.jsonl."""
    def __init__(self, storage: StorageManager, llm: LLMClient):
        self.storage = storage
        self.llm = llm
        self.name = "Capture Agent (Manas)"

    def capture(self, text: str, source: str = "cli", timestamp: Optional[str] = None) -> InboxItem:
        if not timestamp:
            timestamp = datetime.now().isoformat()
        item = InboxItem(text=text.strip(), source=source, timestamp=timestamp)
        self.storage.append_inbox_item(item)
        self.llm.log_event(
            self.name, "success",
            f"Captured new raw entry [{item.id}] from {source}: '{item.text[:50]}...'",
            {"id": item.id, "text": item.text, "source": source}
        )
        return item

    def capture_file(self, filepath: str) -> List[InboxItem]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        items = []
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # If file has multiple lines/bullets, split or capture as single entry
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            for line in lines:
                if line.startswith("-") or line.startswith("*"):
                    line = line[1:].strip()
                if len(line) > 3:
                    items.append(self.capture(line, source=f"file:{os.path.basename(filepath)}"))
        
        self.llm.log_event(
            self.name, "success",
            f"Ingested {len(items)} entries from file {os.path.basename(filepath)}.",
            {"filepath": filepath, "count": len(items)}
        )
        return items


class ClassifierAgent:
    """Buddhi — Intellect & Discernment: Classifies raw inbox entries using an LLM prompt."""
    def __init__(self, storage: StorageManager, llm: LLMClient):
        self.storage = storage
        self.llm = llm
        self.name = "Classifier Agent (Buddhi)"
        self.system_prompt = (
            "You are the Classifier Agent (Buddhi), responsible for discernment and categorization in Antahkarana OS.\n"
            "Analyze the input text and classify it into:\n"
            "1. type: must be exactly one of [task, idea, reference, waiting-on, someday].\n"
            "   - task: actionable item requiring work by the user.\n"
            "   - idea: creative brainstorming, concept, or exploration.\n"
            "   - reference: informational link, document, note, or receipt.\n"
            "   - waiting-on: item blocked by or awaiting a third party.\n"
            "   - someday: aspirational, long-term goal without timeline.\n"
            "2. category: freeform PARA project or area (e.g., 'Work/AI Project', 'Health & Wellness', 'Finance & Admin', 'Home & Life').\n"
            "3. priority: must be one of [high, med, low].\n"
            "4. effort: must be one of [quick, focused, project]. quick=<15m, focused=1-4h, project=multi-day/week.\n"
            "5. reasoning: 1 concise sentence explaining your classification.\n"
            "Respond ONLY with valid JSON format: {\"type\": \"...\", \"category\": \"...\", \"priority\": \"...\", \"effort\": \"...\", \"reasoning\": \"...\"}."
        )

    def classify(self, item: InboxItem) -> ClassifiedItem:
        self.llm.log_event(self.name, "thought", f"Analyzing inbox item [{item.id}]: '{item.text}'", {"id": item.id})
        user_prompt = f"INBOX ENTRY ID {item.id}:\nText: \"{item.text}\"\nCaptured At: {item.timestamp}\nSource: {item.source}"
        
        raw_res = self.llm.generate_content(self.name, self.system_prompt, user_prompt, json_mode=True)
        
        try:
            data = json.loads(raw_res)
            c_type = ItemType.from_str(str(data.get("type", "task"))).value
            c_cat = str(data.get("category", "General")).strip()
            c_prio = Priority.from_str(str(data.get("priority", "med"))).value
            c_eff = Effort.from_str(str(data.get("effort", "focused"))).value
            c_reason = str(data.get("reasoning", "Classified by AI discernment model."))
        except Exception as e:
            self.llm.log_event(self.name, "error", f"JSON parse fallback for [{item.id}]: {str(e)}", {"raw": raw_res})
            c_type = "task"
            c_cat = "General"
            c_prio = "med"
            c_eff = "focused"
            c_reason = "Fallback classification due to formatting variance."

        classified = ClassifiedItem(
            inbox_id=item.id,
            text=item.text,
            timestamp=item.timestamp,
            item_type=c_type,
            category=c_cat,
            priority=c_prio,
            effort=c_eff,
            reasoning=c_reason
        )
        self.llm.log_event(
            self.name, "success",
            f"Classified [{item.id}] -> {c_type.upper()} in [{c_cat}] ({c_prio} prio, {c_eff} effort).",
            classified.model_dump()
        )
        return classified


class RouterAgent:
    """Chitta — Memory & Storage: Routes classified items into PARA structured storage."""
    def __init__(self, storage: StorageManager, llm: LLMClient):
        self.storage = storage
        self.llm = llm
        self.name = "Intake/Router Agent (Chitta)"

    def route(self, item: ClassifiedItem) -> Dict[str, Any]:
        self.llm.log_event(self.name, "thought", f"Routing classified item [{item.inbox_id}] ({item.item_type})...", {"type": item.item_type})
        now_str = datetime.now().isoformat()
        
        target_store = "unknown"
        routed_id = item.inbox_id
        
        if item.item_type in ["task", "waiting-on"]:
            task = TaskItem(
                id=item.inbox_id,
                text=item.text,
                item_type=item.item_type,
                category=item.category,
                priority=item.priority,
                effort=item.effort,
                status="open",
                created_at=item.timestamp,
                updated_at=now_str,
                stale=False
            )
            self.storage.insert_task(task)
            target_store = "tasks.db (SQLite)"
            
        elif item.item_type in ["reference", "idea"]:
            note = NoteItem(
                id=item.inbox_id,
                text=f"{item.text}\n> *AI Reasoning*: {item.reasoning}",
                category=item.category,
                created_at=item.timestamp,
                item_type=item.item_type
            )
            self.storage.append_note(note)
            target_store = "notes.md (PARA Resources/Ideas)"
            
        elif item.item_type == "someday":
            arch = ArchiveItem(
                id=item.inbox_id,
                text=item.text,
                category=item.category,
                created_at=item.timestamp,
                reason=item.reasoning
            )
            self.storage.append_archive(arch)
            target_store = "archive.md (PARA Archive / Someday)"
        else:
            # Fallback to tasks
            task = TaskItem(
                id=item.inbox_id,
                text=item.text,
                item_type="task",
                category=item.category,
                priority=item.priority,
                effort=item.effort,
                status="open",
                created_at=item.timestamp,
                updated_at=now_str
            )
            self.storage.insert_task(task)
            target_store = "tasks.db (Fallback)"

        # Remove from inbox
        self.storage.remove_inbox_item(item.inbox_id)
        
        self.llm.log_event(
            self.name, "success",
            f"Successfully routed [{item.inbox_id}] into {target_store}. Removed from inbox.",
            {"id": item.inbox_id, "destination": target_store}
        )
        return {"id": routed_id, "destination": target_store, "type": item.item_type}


class ReviewerAgent:
    """Ahamkara — Self-Reflection & Consciousness: EOD/EOW review, stale detection, reflection."""
    def __init__(self, storage: StorageManager, llm: LLMClient):
        self.storage = storage
        self.llm = llm
        self.name = "Reviewer Agent (Ahamkara)"
        self.system_prompt = (
            "You are the Reviewer Agent (Ahamkara), responsible for self-reflection and consciousness in Antahkarana OS.\n"
            "Analyze the execution metrics and stale tasks provided. Generate exactly 3 deep, probing self-reflection questions "
            "tailored to the user's specific projects, completion bottlenecks, and stalled items (>3 days untouched).\n"
            "The questions should inspire breakthrough thinking and accountability without being judgmental.\n"
            "Respond ONLY with valid JSON format: {\"reflections\": [\"Question 1...\", \"Question 2...\", \"Question 3...\"]}."
        )

    def review(self) -> ReviewDigest:
        self.llm.log_event(self.name, "start", "Initiating EOD/EOW execution review and stale task audit...", {})
        
        # 1. Update stale flags (>3 days untouched)
        stale_tasks = self.storage.update_stale_flags()
        
        # 2. Get task stats
        all_tasks = self.storage.get_tasks()
        completed = [t for t in all_tasks if t.status == "completed"]
        open_tasks = [t for t in all_tasks if t.status != "completed"]
        
        comp_count = len(completed)
        open_count = len(open_tasks)
        total = comp_count + open_count
        comp_rate = (comp_count / total * 100.0) if total > 0 else 0.0
        
        self.llm.log_event(
            self.name, "thought",
            f"Metrics computed: {comp_count} completed, {open_count} open ({comp_rate:.1f}% rate). Identified {len(stale_tasks)} stale items.",
            {"completed": comp_count, "open": open_count, "stale": len(stale_tasks)}
        )
        
        # 3. Formulate LLM prompt for reflections
        stale_desc = "\n".join([f"- [{t.id}] '{t.text}' (Category: {t.category}, Priority: {t.priority}, Created: {t.created_at[:10]})" for t in stale_tasks])
        if not stale_desc:
            stale_desc = "No stale items! Excellent momentum across all projects."
            
        user_prompt = (
            f"EXECUTION METRICS:\nTotal Tasks Tracked: {total}\nCompleted Tasks: {comp_count}\nOpen Tasks: {open_count}\n"
            f"Completion Rate: {comp_rate:.1f}%\n\nSTALE TASKS (>3 Days Untouched):\n{stale_desc}\n\n"
            "Generate 3 customized reflection questions based on these specific projects and metrics."
        )
        
        raw_res = self.llm.generate_content(self.name, self.system_prompt, user_prompt, json_mode=True)
        
        try:
            data = json.loads(raw_res)
            reflections = data.get("reflections", [
                "What is the primary bottleneck preventing progress on your open tasks?",
                "How can you better structure your daily energy to tackle high-priority project items?",
                "Are your current commitments aligned with your highest long-term aspirations?"
            ])
        except Exception:
            reflections = [
                "You have stale items lingering in your list for over 3 days. What underlying resistance is preventing completion?",
                "Looking at your active tasks, are you dedicating enough uninterrupted focus blocks to high-impact project items?",
                "How can you streamline your daily capture routines to clear administrative tasks faster?"
            ]
            
        digest = ReviewDigest(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            completed_count=comp_count,
            open_count=open_count,
            completion_rate_pct=comp_rate,
            stale_items=stale_tasks,
            reflections=reflections[:3]
        )
        
        self.storage.save_digest(digest)
        self.llm.log_event(
            self.name, "success",
            f"Review Digest generated and saved to digest.md with {len(stale_tasks)} stale items flagged.",
            digest.model_dump()
        )
        return digest


class PlannerAgent:
    """Viveka — Executive Director: Eisenhower matrix prioritization (Urgent vs. Important)."""
    def __init__(self, storage: StorageManager, llm: LLMClient):
        self.storage = storage
        self.llm = llm
        self.name = "Planner Agent (Viveka)"
        self.system_prompt = (
            "You are the Planner Agent (Viveka), responsible for executive prioritization and the Eisenhower Matrix in Antahkarana OS.\n"
            "Analyze the open tasks provided and assign each task to exactly one of the 4 Eisenhower Quadrants:\n"
            "- Q1 - Do Now (Urgent & Important): Critical deadlines, emergencies, high-impact immediate bugs or financial tasks.\n"
            "- Q2 - Schedule (Important, Not Urgent): Deep work, AI project architecture, health routines, strategic planning.\n"
            "- Q3 - Delegate / Quick Win (Urgent, Not Important): Quick administrative chores, batchable emails, minor fixes.\n"
            "- Q4 - Reconsider (Neither Urgent nor Important): Low ROI tasks that should be postponed or eliminated.\n\n"
            "Provide a strategic executive summary (2 sentences) and allocate every task ID.\n"
            "Respond ONLY with valid JSON format:\n"
            "{\n"
            "  \"summary\": \"Executive summary text...\",\n"
            "  \"assignments\": [\n"
            "    {\"task_id\": \"ID\", \"quadrant\": \"Q1 - Do Now (Urgent & Important)\", \"reason\": \"1 concise sentence why\"}\n"
            "  ]\n"
            "}."
        )

    def plan(self, digest: Optional[ReviewDigest] = None) -> PlanDigest:
        self.llm.log_event(self.name, "start", "Initiating Eisenhower Matrix prioritization analysis...", {})
        
        open_tasks = [t for t in self.storage.get_tasks() if t.status != "completed"]
        if not open_tasks:
            empty_plan = PlanDigest(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                q1_do_now=[], q2_schedule=[], q3_delegate=[], q4_eliminate=[],
                summary="No open tasks remaining! Your task matrix is completely clear."
            )
            self.storage.save_plan(empty_plan)
            self.llm.log_event(self.name, "success", "No open tasks to plan. Generated clean slate plan.", {})
            return empty_plan

        tasks_str = "\n".join([f"- ID: {t.id} | Text: '{t.text}' | Category: {t.category} | Priority: {t.priority} | Effort: {t.effort} | Stale: {t.stale}" for t in open_tasks])
        
        user_prompt = f"OPEN TASKS TO PRIORITIZE ({len(open_tasks)} items):\n{tasks_str}\n\nAllocate every single task ID to an Eisenhower Quadrant with rationale."
        
        raw_res = self.llm.generate_content(self.name, self.system_prompt, user_prompt, json_mode=True)
        
        task_map = {t.id: t for t in open_tasks}
        q1, q2, q3, q4 = [], [], [], []
        summary_text = "Executive priority ranking balancing immediate urgent deliverables with strategic project execution."
        
        try:
            data = json.loads(raw_res)
            summary_text = data.get("summary", summary_text)
            assignments = data.get("assignments", [])
            
            assigned_ids = set()
            for asc in assignments:
                t_id = str(asc.get("task_id", "")).strip()
                if t_id in task_map:
                    assigned_ids.add(t_id)
                    task_obj = task_map[t_id]
                    quad = str(asc.get("quadrant", "Q2")).upper()
                    reason = str(asc.get("reason", "Allocated by executive prioritization engine."))
                    
                    item = EisenhowerItem(task=task_obj, quadrant=quad, reason=reason)
                    if "Q1" in quad or "DO NOW" in quad:
                        q1.append(item)
                    elif "Q3" in quad or "DELEGATE" in quad or "QUICK" in quad:
                        q3.append(item)
                    elif "Q4" in quad or "RECONSIDER" in quad or "ELIMINATE" in quad:
                        q4.append(item)
                    else:
                        q2.append(item)
                        
            # Any unassigned open tasks go to Q2 by default
            for t_id, t_obj in task_map.items():
                if t_id not in assigned_ids:
                    q2.append(EisenhowerItem(
                        task=t_obj,
                        quadrant="Q2 - Schedule (Important, Not Urgent)",
                        reason="High-value project item assigned to scheduled deep work."
                    ))
        except Exception as e:
            self.llm.log_event(self.name, "error", f"JSON parse fallback in planner: {str(e)}", {"raw": raw_res})
            # Heuristic fallback allocation
            for t_obj in open_tasks:
                if t_obj.priority == "high" or t_obj.stale:
                    q1.append(EisenhowerItem(task=t_obj, quadrant="Q1 - Do Now (Urgent & Important)", reason="High priority or stale task requiring immediate action."))
                elif t_obj.effort == "quick":
                    q3.append(EisenhowerItem(task=t_obj, quadrant="Q3 - Delegate / Quick Win (Urgent, Not Important)", reason="Quick win item that can be cleared rapidly."))
                elif t_obj.priority == "low":
                    q4.append(EisenhowerItem(task=t_obj, quadrant="Q4 - Reconsider (Neither)", reason="Low priority item with minimal immediate urgency."))
                else:
                    q2.append(EisenhowerItem(task=t_obj, quadrant="Q2 - Schedule (Important, Not Urgent)", reason="Strategic project task requiring dedicated focus blocks."))

        plan = PlanDigest(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            q1_do_now=q1,
            q2_schedule=q2,
            q3_delegate=q3,
            q4_eliminate=q4,
            summary=summary_text
        )
        
        self.storage.save_plan(plan)
        self.llm.log_event(
            self.name, "success",
            f"Action Plan generated and saved to plan.md (Q1:{len(q1)}, Q2:{len(q2)}, Q3:{len(q3)}, Q4:{len(q4)}).",
            {"q1": len(q1), "q2": len(q2), "q3": len(q3), "q4": len(q4)}
        )
        return plan


class AntahkaranaPipeline:
    """Orchestrates the full 5-agent pipeline."""
    def __init__(self, storage: Optional[StorageManager] = None, llm: Optional[LLMClient] = None):
        self.storage = storage or StorageManager()
        self.llm = llm or LLMClient()
        self.capture_agent = CaptureAgent(self.storage, self.llm)
        self.classifier_agent = ClassifierAgent(self.storage, self.llm)
        self.router_agent = RouterAgent(self.storage, self.llm)
        self.reviewer_agent = ReviewerAgent(self.storage, self.llm)
        self.planner_agent = PlannerAgent(self.storage, self.llm)

    def run_full_pipeline(self) -> Dict[str, Any]:
        self.llm.log_event("Sutradhara (Orchestrator)", "start", "🔥 Triggering Full 5-Agent Antahkarana OS Pipeline!", {})
        
        # 1. Process Inbox (Buddhi -> Chitta)
        inbox_items = self.storage.get_inbox_items()
        routed_results = []
        for item in inbox_items:
            classified = self.classifier_agent.classify(item)
            res = self.router_agent.route(classified)
            routed_results.append(res)
            
        # 2. Review (Ahamkara)
        digest = self.reviewer_agent.review()
        
        # 3. Plan (Viveka)
        plan = self.planner_agent.plan(digest)
        
        summary = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "inbox_processed": len(routed_results),
            "routed": routed_results,
            "metrics": {
                "completed_tasks": digest.completed_count,
                "open_tasks": digest.open_count,
                "stale_tasks": len(digest.stale_items),
                "completion_rate": f"{digest.completion_rate_pct:.1f}%"
            },
            "eisenhower_counts": {
                "q1_do_now": len(plan.q1_do_now),
                "q2_schedule": len(plan.q2_schedule),
                "q3_delegate": len(plan.q3_delegate),
                "q4_eliminate": len(plan.q4_eliminate)
            }
        }
        
        self.llm.log_event("Sutradhara (Orchestrator)", "success", "✨ Full Pipeline Execution Completed Successfully!", summary)
        return summary
