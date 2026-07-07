# ⏱️ Antahkarana OS — 2-Minute Presenter Demo Script

This reading script is timed and formatted for presenting **Antahkarana OS** during a live demo, video walkthrough, or team pitch. You can present this using either the Terminal CLI (`python cli.py demo`) or the visual Web UI (`python cli.py serve` -> http://localhost:8000).

---

### 0:00 – 0:20 | The Problem & The Vedic Solution
* **Action**: Open terminal or show the glowing Web UI Dashboard.
* **Speaker**: 
> "Daily personal productivity breaks down because capture is frictionless, but organization is hard. We dump thoughts into notes apps, where they rot and overwhelm us. 
> 
> Meet **Antahkarana OS**—named after the Vedic concept of the functional mind. Instead of one giant LLM prompt, we built a 5-agent hierarchy where each AI role mimics a layer of human cognition to close the loop from daily unstructured capture to executive action."

---

### 0:20 – 0:45 | Step 1 & 2: Manas (Capture), Buddhi (Classifier) & Chitta (Router)
* **Action**: Click **"🌱 Seed Demo Data"** on the UI, then click **"🚀 Run Full 5-Agent Pipeline"** (or run `python cli.py demo`). Point to the live Inbox and Agent Console.
* **Speaker**: 
> "First is **Manas**, our capture agent. It just ingested 10 messy entries across work, health, finance, and home—no categorization required.
> 
> Immediately, **Buddhi** (the discerning intellect agent) evaluates each item, tagging its type, PARA category, priority, and effort level. Then **Chitta** (the memory router agent) directs actionable tasks into an SQLite database (`tasks.db`), informational references into structured Markdown (`notes.md`), and someday goals into an archive (`archive.md`). Notice our Inbox is now completely clear!"

---

### 0:45 – 1:15 | Step 3: Ahamkara (Reviewer Agent & Stale Task Audit)
* **Action**: Switch to the **"🪞 3. Ahamkara (EOD/EOW Review)"** tab or point to Step 3 in terminal output. Highlight the pulsing red **"⚠️ STALE"** badges.
* **Speaker**: 
> "At the end of the day or week, we run **Ahamkara**, our self-reflective review agent. It computes our completion velocity and scans the database for execution bottlenecks.
> 
> Look right here: Ahamkara detected 3 tasks that have been sitting open for over 3 days untouched and flagged them with high-priority **Stale Alerts**. Then, it generated three deep, customized AI reflection questions to help us break through our project resistance without feeling judged."

---

### 1:15 – 1:45 | Step 4: Viveka (Executive Eisenhower Planner)
* **Action**: Switch to the **"🎯 4. Viveka (Eisenhower Plan)"** tab or point to Step 4 in terminal output.
* **Speaker**: 
> "Finally, we meet **Viveka**, our executive planning agent. Viveka evaluates our remaining open tasks and our review digest to build a strategic execution plan.
> 
> It automatically sorts every single item into the classic **Eisenhower 4-Quadrant Matrix**: urgent fires go into *Q1 (Do Now)*, deep AI architectural work is protected in *Q2 (Schedule)*, quick admin chores go to *Q3 (Delegate)*, and low-ROI distractions are relegated to *Q4 (Eliminate)*."

---

### 1:45 – 2:00 | Conclusion & Wrap-up
* **Action**: Switch to the **"📡 5. Live Telemetry"** console tab showing real-time streaming logs.
* **Speaker**: 
> "Antahkarana OS runs 100% locally with Python, SQLite, and Vanilla Web technologies. It supports Gemini and OpenAI, and includes an intelligent deterministic simulation engine so this entire E2E loop runs flawlessly anywhere.
> 
> That is how Antahkarana OS turns daily chaos into a calm, structured second brain. Thank you!"
