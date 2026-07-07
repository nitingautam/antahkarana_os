import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from models import (
    InboxItem, ClassifiedItem, TaskItem, NoteItem, ArchiveItem,
    ReviewDigest, PlanDigest, TaskStatus
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INBOX_FILE = os.path.join(DATA_DIR, "inbox.jsonl")
TASKS_DB = os.path.join(DATA_DIR, "tasks.db")
NOTES_FILE = os.path.join(DATA_DIR, "notes.md")
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive.md")
DIGEST_FILE = os.path.join(DATA_DIR, "digest.md")
PLAN_FILE = os.path.join(DATA_DIR, "plan.md")


class StorageManager:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.inbox_file = os.path.join(self.data_dir, "inbox.jsonl")
        self.tasks_db = os.path.join(self.data_dir, "tasks.db")
        self.notes_file = os.path.join(self.data_dir, "notes.md")
        self.archive_file = os.path.join(self.data_dir, "archive.md")
        self.digest_file = os.path.join(self.data_dir, "digest.md")
        self.digest_json = os.path.join(self.data_dir, "digest.json")
        self.plan_file = os.path.join(self.data_dir, "plan.md")
        self.plan_json = os.path.join(self.data_dir, "plan.json")
        self.init_storage()

    def init_storage(self):
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.inbox_file):
            with open(self.inbox_file, "w", encoding="utf-8") as f:
                pass
        if not os.path.exists(self.notes_file):
            with open(self.notes_file, "w", encoding="utf-8") as f:
                f.write("# PARA Resources & Ideas (Notes)\n\n")
        if not os.path.exists(self.archive_file):
            with open(self.archive_file, "w", encoding="utf-8") as f:
                f.write("# PARA Archive & Someday / Maybe\n\n")
        
        with sqlite3.connect(self.tasks_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    effort TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    stale INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    # --- Inbox Methods ---
    def append_inbox_item(self, item: InboxItem) -> InboxItem:
        with open(self.inbox_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(item.model_dump()) + "\n")
        return item

    def get_inbox_items(self) -> List[InboxItem]:
        items = []
        if not os.path.exists(self.inbox_file):
            return items
        with open(self.inbox_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        items.append(InboxItem(**data))
                    except Exception:
                        continue
        return items

    def remove_inbox_item(self, item_id: str) -> bool:
        items = self.get_inbox_items()
        remaining = [item for item in items if item.id != item_id]
        if len(remaining) == len(items):
            return False
        with open(self.inbox_file, "w", encoding="utf-8") as f:
            for item in remaining:
                f.write(json.dumps(item.model_dump()) + "\n")
        return True

    def clear_inbox(self):
        with open(self.inbox_file, "w", encoding="utf-8") as f:
            pass

    # --- Task SQLite Methods ---
    def insert_task(self, task: TaskItem) -> TaskItem:
        with sqlite3.connect(self.tasks_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tasks 
                (id, text, item_type, category, priority, effort, status, created_at, updated_at, stale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.text, task.item_type, task.category, task.priority,
                task.effort, task.status, task.created_at, task.updated_at, 1 if task.stale else 0
            ))
            conn.commit()
        return task

    def get_tasks(self, status: Optional[str] = None, category: Optional[str] = None) -> List[TaskItem]:
        query = "SELECT id, text, item_type, category, priority, effort, status, created_at, updated_at, stale FROM tasks WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        
        tasks = []
        with sqlite3.connect(self.tasks_db) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for row in rows:
                tasks.append(TaskItem(
                    id=row[0], text=row[1], item_type=row[2], category=row[3],
                    priority=row[4], effort=row[5], status=row[6], created_at=row[7],
                    updated_at=row[8], stale=bool(row[9])
                ))
        return tasks

    def update_task_status(self, task_id: str, new_status: str) -> Optional[TaskItem]:
        now_str = datetime.now().isoformat()
        with sqlite3.connect(self.tasks_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
            """, (new_status, now_str, task_id))
            conn.commit()
        tasks = self.get_tasks()
        for t in tasks:
            if t.id == task_id:
                return t
        return None

    def update_stale_flags(self) -> List[TaskItem]:
        """Marks open tasks untouched for > 3 days as stale."""
        all_tasks = self.get_tasks()
        stale_tasks = []
        now = datetime.now()
        
        with sqlite3.connect(self.tasks_db) as conn:
            cursor = conn.cursor()
            for task in all_tasks:
                if task.status != "completed":
                    try:
                        # try parsing isoformat
                        created_dt = datetime.fromisoformat(task.created_at.replace("Z", "+00:00").split("+")[0])
                    except Exception:
                        created_dt = now - timedelta(days=4)
                    
                    if (now - created_dt).total_seconds() > 3 * 86400:
                        task.stale = True
                        stale_tasks.append(task)
                        cursor.execute("UPDATE tasks SET stale = 1 WHERE id = ?", (task.id,))
                    else:
                        task.stale = False
                        cursor.execute("UPDATE tasks SET stale = 0 WHERE id = ?", (task.id,))
            conn.commit()
        return stale_tasks

    def clear_tasks(self):
        with sqlite3.connect(self.tasks_db) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks")
            conn.commit()

    # --- Notes Markdown Methods ---
    def append_note(self, note: NoteItem) -> NoteItem:
        content = f"\n### [{note.category}] - {note.item_type.upper()}\n"
        content += f"- **Date**: {note.created_at[:10]}\n"
        content += f"- **ID**: `{note.id}`\n"
        content += f"- **Content**: {note.text}\n"
        with open(self.notes_file, "a", encoding="utf-8") as f:
            f.write(content)
        return note

    def get_notes_content(self) -> str:
        if not os.path.exists(self.notes_file):
            return "# PARA Resources & Ideas (Notes)\n\n"
        with open(self.notes_file, "r", encoding="utf-8") as f:
            return f.read()

    def clear_notes(self):
        with open(self.notes_file, "w", encoding="utf-8") as f:
            f.write("# PARA Resources & Ideas (Notes)\n\n")

    # --- Archive Markdown Methods ---
    def append_archive(self, item: ArchiveItem) -> ArchiveItem:
        content = f"\n### [{item.category}] - Someday / Maybe\n"
        content += f"- **Date**: {item.created_at[:10]}\n"
        content += f"- **ID**: `{item.id}`\n"
        if item.reason:
            content += f"- **Reason/Context**: {item.reason}\n"
        content += f"- **Content**: {item.text}\n"
        with open(self.archive_file, "a", encoding="utf-8") as f:
            f.write(content)
        return item

    def get_archive_content(self) -> str:
        if not os.path.exists(self.archive_file):
            return "# PARA Archive & Someday / Maybe\n\n"
        with open(self.archive_file, "r", encoding="utf-8") as f:
            return f.read()

    def clear_archive(self):
        with open(self.archive_file, "w", encoding="utf-8") as f:
            f.write("# PARA Archive & Someday / Maybe\n\n")

    # --- Digest and Plan Outputs ---
    def save_digest(self, digest: ReviewDigest):
        content = f"# 📊 Antahkarana OS - Review Digest\n"
        content += f"**Generated**: {digest.timestamp}\n\n"
        content += f"## 📈 Execution Metrics\n"
        content += f"- **Completed Tasks**: {digest.completed_count}\n"
        content += f"- **Open Tasks**: {digest.open_count}\n"
        content += f"- **Completion Rate**: {digest.completion_rate_pct:.1f}%\n\n"
        
        content += f"## ⚠️ Stale Tasks (>3 Days Untouched)\n"
        if digest.stale_items:
            for st in digest.stale_items:
                content += f"- `[{st.id}]` **{st.text}** *(Category: {st.category}, Priority: {st.priority}, Created: {st.created_at[:10]})*\n"
        else:
            content += f"*No stale items detected. Clean momentum!* ✨\n"
        content += "\n"
        
        content += f"## 🪞 Self-Reflection & Guidance\n"
        for idx, ref in enumerate(digest.reflections, 1):
            content += f"### Question {idx}\n> {ref}\n\n"
            
        with open(self.digest_file, "w", encoding="utf-8") as f:
            f.write(content)
        with open(self.digest_json, "w", encoding="utf-8") as f:
            f.write(digest.model_dump_json(indent=2))

    def save_plan(self, plan: PlanDigest):
        content = f"# 🎯 Antahkarana OS - Eisenhower Action Plan\n"
        content += f"**Generated**: {plan.timestamp}\n\n"
        content += f"## 🧭 Executive Summary\n{plan.summary}\n\n"
        
        content += f"## 🔥 Q1 - Do Now (Urgent & Important)\n"
        if plan.q1_do_now:
            for idx, item in enumerate(plan.q1_do_now, 1):
                content += f"{idx}. `[{item.task.id}]` **{item.task.text}** *(Project: {item.task.category}, Effort: {item.task.effort})*\n"
                content += f"   - *Why*: {item.reason}\n"
        else:
            content += f"*No immediate fires to put out!* 🎉\n"
        content += "\n"
        
        content += f"## 📅 Q2 - Schedule & Focus (Important, Not Urgent)\n"
        if plan.q2_schedule:
            for idx, item in enumerate(plan.q2_schedule, 1):
                content += f"{idx}. `[{item.task.id}]` **{item.task.text}** *(Project: {item.task.category}, Effort: {item.task.effort})*\n"
                content += f"   - *Why*: {item.reason}\n"
        else:
            content += f"*No scheduled deep work items.*\n"
        content += "\n"
        
        content += f"## ⚡ Q3 - Delegate / Quick Wins (Urgent, Not Important)\n"
        if plan.q3_delegate:
            for idx, item in enumerate(plan.q3_delegate, 1):
                content += f"{idx}. `[{item.task.id}]` **{item.task.text}** *(Project: {item.task.category}, Effort: {item.task.effort})*\n"
                content += f"   - *Why*: {item.reason}\n"
        else:
            content += f"*No quick wins or delegation items.*\n"
        content += "\n"
        
        content += f"## 🗑️ Q4 - Reconsider / Eliminate (Neither Urgent nor Important)\n"
        if plan.q4_eliminate:
            for idx, item in enumerate(plan.q4_eliminate, 1):
                content += f"{idx}. `[{item.task.id}]` **{item.task.text}** *(Project: {item.task.category}, Effort: {item.task.effort})*\n"
                content += f"   - *Why*: {item.reason}\n"
        else:
            content += f"*Clean slate! No low-value items found.*\n"
        content += "\n"

        with open(self.plan_file, "w", encoding="utf-8") as f:
            f.write(content)
        with open(self.plan_json, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))

    def get_digest_content(self) -> str:
        if not os.path.exists(self.digest_file):
            return "# 📊 Antahkarana OS - Review Digest\n\n*No review digest generated yet. Run Reviewer Agent.*"
        with open(self.digest_file, "r", encoding="utf-8") as f:
            return f.read()

    def get_plan_content(self) -> str:
        if not os.path.exists(self.plan_file):
            return "# 🎯 Antahkarana OS - Eisenhower Action Plan\n\n*No action plan generated yet. Run Planner Agent.*"
        with open(self.plan_file, "r", encoding="utf-8") as f:
            return f.read()

    def reset_all_data(self):
        self.clear_inbox()
        self.clear_tasks()
        self.clear_notes()
        self.clear_archive()
        if os.path.exists(self.digest_file):
            os.remove(self.digest_file)
        if os.path.exists(self.digest_json):
            os.remove(self.digest_json)
        if os.path.exists(self.plan_file):
            os.remove(self.plan_file)
        if os.path.exists(self.plan_json):
            os.remove(self.plan_json)
        self.init_storage()
