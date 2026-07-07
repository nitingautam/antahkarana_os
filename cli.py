import os
import sys
import argparse
import json
import time
from datetime import datetime

# Fix Windows console encoding for emoji support
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from storage import StorageManager
from llm_client import LLMClient
from agents import AntahkaranaPipeline
from seed_data import seed_sample_data

# ANSI Color Codes for terminal formatting
CYAN = "\033[96m"
GOLD = "\033[93m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{CYAN}{BOLD}========================================================================{RESET}")
    print(f"{GOLD}{BOLD} 🧘 ANTAHKARANA OS (Second Brain) — {title}{RESET}")
    print(f"{CYAN}{BOLD}========================================================================{RESET}\n")

def print_step(step_num: int, title: str, desc: str):
    print(f"\n{MAGENTA}{BOLD}[STEP {step_num}] {title}{RESET} — {desc}")
    print(f"{CYAN}------------------------------------------------------------------------{RESET}")

def run_demo():
    print_header("AUTOMATED 2-MINUTE DEMO PIPELINE")
    print(f"{GREEN}Initializing storage and seeding sample data...{RESET}")
    
    storage = StorageManager()
    llm = LLMClient()
    pipeline = AntahkaranaPipeline(storage, llm)
    
    # Add simple listener to print logs
    def log_printer(ev):
        symbol = "ℹ️"
        if ev.event_type == "start": symbol = "🚀"
        elif ev.event_type == "thought": symbol = "🧠"
        elif ev.event_type == "llm_call": symbol = "⚡"
        elif ev.event_type == "success": symbol = "✅"
        elif ev.event_type == "error": symbol = "❌"
        print(f"  {symbol} [{ev.timestamp}] {BOLD}{ev.agent_name}{RESET}: {ev.message}")
        
    llm.add_listener(log_printer)
    
    # Step 1: Seed
    print_step(1, "MANAS (Capture Agent)", "Seeding 10 unstructured entries across all 5 types into inbox.jsonl")
    seed_sample_data(storage)
    inbox = storage.get_inbox_items()
    print(f"\n{GOLD}Inbox currently contains {len(inbox)} items:{RESET}")
    for idx, item in enumerate(inbox[:4], 1):
        print(f"  {idx}. `[{item.id}]` \"{item.text[:60]}...\" ({item.source})")
    print(f"  ... and {len(inbox)-4} more.\n")
    time.sleep(1)

    # Step 2: Classify & Route
    print_step(2, "BUDDHI & CHITTA (Classifier & Router Agents)", "Discernment classification & PARA structured memory routing")
    print(f"{GREEN}Processing all inbox items through AI Classifier and routing to tasks.db, notes.md, archive.md...{RESET}\n")
    
    routed_items = []
    for item in inbox:
        classified = pipeline.classifier_agent.classify(item)
        res = pipeline.router_agent.route(classified)
        routed_items.append(res)
        time.sleep(0.15)
        
    print(f"\n{GOLD}PARA Storage Summary after routing:{RESET}")
    tasks = storage.get_tasks()
    print(f"  📁 tasks.db (Actionable): {len(tasks)} tasks tracked.")
    print(f"  📓 notes.md (References & Ideas): Updated with headings and reasoning.")
    print(f"  🗄️ archive.md (Someday / Maybe): Updated with long-term aspirations.\n")
    time.sleep(1)

    # Step 3: Review
    print_step(3, "AHAMKARA (Reviewer Agent)", "EOD/EOW Reflection, completion velocity & stale task detection")
    print(f"{GREEN}Analyzing database for items untouched > 3 days and generating personalized self-reflections...{RESET}\n")
    digest = pipeline.reviewer_agent.review()
    
    print(f"\n{GOLD}Review Digest Results:{RESET}")
    print(f"  📊 Completion Rate: {digest.completion_rate_pct:.1f}% ({digest.completed_count} completed / {digest.open_count} open)")
    print(f"  ⚠️ Stale Items (>3 Days Untouched): {len(digest.stale_items)} tasks flagged!")
    for st in digest.stale_items:
        print(f"     -> `[{st.id}]` {st.text} ({st.priority} priority, created {st.created_at[:10]})")
    print(f"\n{GOLD}🪞 Self-Reflection Questions Generated:{RESET}")
    for idx, ref in enumerate(digest.reflections, 1):
        print(f"  {idx}. \"{ref}\"")
    print()
    time.sleep(1)

    # Step 4: Plan
    print_step(4, "VIVEKA (Planner Agent)", "Executive prioritization via Eisenhower 4-Quadrant Matrix")
    print(f"{GREEN}Ranking open tasks into Do Now, Schedule, Delegate, and Eliminate...{RESET}\n")
    plan = pipeline.planner_agent.plan(digest)
    
    print(f"\n{GOLD}Eisenhower Matrix Plan generated in plan.md:{RESET}")
    print(f"  🔥 Q1 - Do Now (Urgent & Important): {len(plan.q1_do_now)} items")
    for q in plan.q1_do_now:
        print(f"     -> `[{q.task.id}]` {q.task.text} ({q.reason})")
    print(f"  📅 Q2 - Schedule & Focus: {len(plan.q2_schedule)} items")
    print(f"  ⚡ Q3 - Delegate / Quick Win: {len(plan.q3_delegate)} items")
    print(f"  🗑️ Q4 - Reconsider / Eliminate: {len(plan.q4_eliminate)} items")
    
    print_header("DEMO PIPELINE COMPLETE! 🧘✨")
    print(f"{GREEN}All files generated in ./data/ (inbox.jsonl, tasks.db, notes.md, archive.md, digest.md, plan.md).{RESET}")
    print(f"{CYAN}To launch the visual interactive web UI, run: {BOLD}python cli.py serve{RESET}\n")

def main():
    parser = argparse.ArgumentParser(description="Antahkarana OS — Multi-Agent Personal Productivity System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Capture command
    cap_parser = subparsers.add_parser("capture", help="Capture raw note or text file into Inbox")
    cap_parser.add_argument("text", nargs="?", help="Text string to capture")
    cap_parser.add_argument("-f", "--file", help="Path to text file to capture")
    
    # Seed & Clean commands
    subparsers.add_parser("seed", help="Reset storage and seed sample data")
    subparsers.add_parser("clean", help="Wipe all data and reset storage to completely empty slate")
    subparsers.add_parser("reset", help="Alias for clean (wipe all data)")
    
    # Pipeline commands
    subparsers.add_parser("classify", help="Run Classifier Agent on inbox items")
    subparsers.add_parser("route", help="Run Router Agent on classified items")
    subparsers.add_parser("review", help="Run Reviewer Agent (generate digest.md)")
    subparsers.add_parser("plan", help="Run Planner Agent (generate plan.md)")
    subparsers.add_parser("demo", help="Run automated 2-minute end-to-end demo pipeline")
    
    # Serve command
    subparsers.add_parser("serve", help="Start visual Web UI server (FastAPI)")
    
    args = parser.parse_args()
    
    storage = StorageManager()
    llm = LLMClient()
    pipeline = AntahkaranaPipeline(storage, llm)
    
    if args.command == "capture":
        if args.file:
            items = pipeline.capture_agent.capture_file(args.file)
            print(f"Captured {len(items)} items from {args.file}")
        elif args.text:
            item = pipeline.capture_agent.capture(args.text)
            print(f"Captured `[{item.id}]`: {item.text}")
        else:
            print("Please provide text string or -f <filepath>.")
            
    elif args.command == "seed":
        seed_sample_data(storage)
        
    elif args.command in ["clean", "reset"]:
        storage.reset_all_data()
        print(f"{GREEN}{BOLD}✅ Wiped all data from database (tasks.db) and archives! System reset to empty slate.{RESET}")
        
    elif args.command == "classify" or args.command == "route":
        print("Running processing pipeline...")
        inbox = storage.get_inbox_items()
        for item in inbox:
            c = pipeline.classifier_agent.classify(item)
            r = pipeline.router_agent.route(c)
            print(f"Routed `[{item.id}]` -> {r['destination']}")
            if llm.gemini_key or llm.openai_key:
                time.sleep(1.0)
            
    elif args.command == "review":
        digest = pipeline.reviewer_agent.review()
        print(f"Review Digest generated: {digest.completed_count} completed, {digest.open_count} open, {len(digest.stale_items)} stale.")
        
    elif args.command == "plan":
        plan = pipeline.planner_agent.plan()
        print(f"Eisenhower Plan generated: Q1:{len(plan.q1_do_now)}, Q2:{len(plan.q2_schedule)}, Q3:{len(plan.q3_delegate)}, Q4:{len(plan.q4_eliminate)}")
        
    elif args.command == "demo":
        run_demo()
        
    elif args.command == "serve":
        import uvicorn
        print(f"{CYAN}{BOLD}Starting Antahkarana OS Web Server at http://localhost:8000 ...{RESET}")
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
