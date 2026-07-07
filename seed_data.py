import os
import sys
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from models import InboxItem
from storage import StorageManager

def seed_sample_data(storage: StorageManager):
    """Resets storage and seeds 10 realistic entries covering all 5 item types with intentional stale timestamps."""
    storage.reset_all_data()
    
    now = datetime.now()
    t_minus_6d = (now - timedelta(days=6)).isoformat()
    t_minus_5d = (now - timedelta(days=5)).isoformat()
    t_minus_4d = (now - timedelta(days=4)).isoformat()
    t_minus_1d = (now - timedelta(days=1)).isoformat()
    t_now = now.isoformat()

    samples = [
        # 1. Stale Task (>3 days old)
        InboxItem(id="tsk-0101", text="Fix memory leak in LLM streaming endpoint before Friday release", timestamp=t_minus_5d, source="cli:seed"),
        # 2. Stale Task (>3 days old)
        InboxItem(id="tsk-0102", text="Schedule annual dentist cleaning and checkup", timestamp=t_minus_4d, source="web:seed"),
        # 3. Fresh Task
        InboxItem(id="tsk-0103", text="Submit Q2 expense reports and receipts to accounting", timestamp=t_minus_1d, source="cli:seed"),
        # 4. Fresh Task
        InboxItem(id="tsk-0104", text="Refactor PARA storage SQLite queries for better concurrency", timestamp=t_now, source="cli:seed"),
        # 5. Idea
        InboxItem(id="ida-0201", text="What if we use Vedic philosophy concepts like Antahkarana to structure AI agent memory hierarchies?", timestamp=t_minus_1d, source="web:seed"),
        # 6. Idea
        InboxItem(id="ida-0202", text="Explore using WebSockets instead of polling for real-time agent activity logs in UI", timestamp=t_now, source="cli:seed"),
        # 7. Reference
        InboxItem(id="ref-0301", text="Read research paper on Tree of Thoughts prompting: https://arxiv.org/abs/2305.10601", timestamp=t_minus_4d, source="web:seed"),
        # 8. Reference
        InboxItem(id="ref-0302", text="Stripe API documentation for webhooks signature verification and retry policies", timestamp=t_now, source="cli:seed"),
        # 9. Waiting-On (Stale >3 days old)
        InboxItem(id="wto-0401", text="Awaiting security review approval from DevOps team for AWS IAM role changes", timestamp=t_minus_6d, source="cli:seed"),
        # 10. Someday / Maybe
        InboxItem(id="smd-0501", text="Eventually build an off-grid solar-powered cabin with satellite internet for coding retreats", timestamp=t_minus_1d, source="web:seed"),
    ]

    for item in samples:
        storage.append_inbox_item(item)
        
    print(f"✅ Successfully seeded {len(samples)} diverse entries into inbox.jsonl (including 3 stale items dated 4-6 days ago!).")
    return samples

if __name__ == "__main__":
    sm = StorageManager()
    seed_sample_data(sm)
