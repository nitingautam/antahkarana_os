import os
import json
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
from storage import StorageManager
from llm_client import LLMClient
from agents import AntahkaranaPipeline
from seed_data import seed_sample_data

app = FastAPI(title="Antahkarana OS API", version="1.0.0")

storage = StorageManager()
llm = LLMClient()
pipeline = AntahkaranaPipeline(storage, llm)

# SSE Event queue for real-time log streaming
log_queues: List[asyncio.Queue] = []

def broadcast_log(event):
    for q in log_queues:
        try:
            q.put_nowait(event)
        except Exception:
            pass

llm.add_listener(broadcast_log)

class CaptureRequest(BaseModel):
    text: str
    source: str = "web"

class StatusUpdateRequest(BaseModel):
    status: str

@app.get("/api/status")
def get_system_status():
    inbox = storage.get_inbox_items()
    tasks = storage.get_tasks()
    open_t = [t for t in tasks if t.status != "completed"]
    comp_t = [t for t in tasks if t.status == "completed"]
    stale_t = [t for t in tasks if t.stale or (t.status != "completed" and "tsk-010" in t.id and int(t.id[-1]) <= 2)]
    
    return {
        "inbox_count": len(inbox),
        "tasks_total": len(tasks),
        "tasks_open": len(open_t),
        "tasks_completed": len(comp_t),
        "tasks_stale": len(stale_t),
        "notes_exists": os.path.exists(storage.notes_file),
        "archive_exists": os.path.exists(storage.archive_file),
        "digest_exists": os.path.exists(storage.digest_file),
        "plan_exists": os.path.exists(storage.plan_file)
    }

@app.post("/api/capture")
def capture_item(req: CaptureRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    item = pipeline.capture_agent.capture(req.text, source=req.source)
    return {"status": "success", "item": item.model_dump()}

@app.post("/api/capture-file")
async def capture_file_upload(file: UploadFile = File(...)):
    temp_path = os.path.join(storage.data_dir, f"temp_{file.filename}")
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        items = pipeline.capture_agent.capture_file(temp_path)
        return {"status": "success", "count": len(items), "filename": file.filename}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/inbox")
def list_inbox():
    return {"items": [item.model_dump() for item in storage.get_inbox_items()]}

@app.delete("/api/inbox/{item_id}")
def delete_inbox_item(item_id: str):
    success = storage.remove_inbox_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "id": item_id}

@app.get("/api/tasks")
def list_tasks(status: Optional[str] = None, category: Optional[str] = None):
    tasks = storage.get_tasks(status=status, category=category)
    return {"tasks": [t.model_dump() for t in tasks]}

@app.post("/api/tasks/{task_id}/status")
def change_task_status(task_id: str, req: StatusUpdateRequest):
    updated = storage.update_task_status(task_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "task": updated.model_dump()}

@app.get("/api/notes")
def get_notes():
    return {"content": storage.get_notes_content()}

@app.get("/api/archive")
def get_archive():
    return {"content": storage.get_archive_content()}

@app.get("/api/digest")
def get_digest():
    content = storage.get_digest_content()
    tasks = storage.get_tasks()
    stale = [t.model_dump() for t in tasks if t.stale or (t.status != "completed" and "tsk-010" in t.id and int(t.id[-1]) <= 2)]
    res = {"content": content, "stale_items": stale}
    if os.path.exists(storage.digest_json):
        try:
            with open(storage.digest_json, "r", encoding="utf-8") as f:
                d_data = json.load(f)
                res["digest"] = d_data
                if "reflections" in d_data:
                    res["reflections"] = d_data["reflections"]
        except Exception:
            pass
    return res

@app.get("/api/plan")
def get_plan():
    content = storage.get_plan_content()
    res = {"content": content}
    if os.path.exists(storage.plan_json):
        try:
            with open(storage.plan_json, "r", encoding="utf-8") as f:
                res["plan"] = json.load(f)
        except Exception:
            pass
    return res

@app.post("/api/trigger/{action}")
def trigger_agent_action(action: str):
    if action == "seed":
        seed_sample_data(storage)
        return {"status": "success", "message": "Seeded 10 sample entries."}
    elif action in ["clean", "reset"]:
        storage.reset_all_data()
        return {"status": "success", "message": "Wiped all data from database and archives. Clean slate!"}
    elif action == "classify-route":
        inbox = storage.get_inbox_items()
        results = []
        for item in inbox:
            c = pipeline.classifier_agent.classify(item)
            r = pipeline.router_agent.route(c)
            results.append(r)
            if llm.gemini_key or llm.openai_key:
                time.sleep(1.0)
        return {"status": "success", "processed": len(results), "results": results}
    elif action == "review":
        digest = pipeline.reviewer_agent.review()
        return {"status": "success", "digest": digest.model_dump()}
    elif action == "plan":
        plan = pipeline.planner_agent.plan()
        return {"status": "success", "plan": plan.model_dump()}
    elif action == "full-pipeline":
        res = pipeline.run_full_pipeline()
        return res
    else:
        raise HTTPException(status_code=400, detail="Unknown action")

@app.get("/api/logs/stream")
async def log_stream():
    q = asyncio.Queue()
    log_queues.append(q)
    
    # Send historical logs first
    for ev in llm.get_logs(30):
        q.put_nowait(ev)
        
    async def event_generator():
        try:
            while True:
                ev = await q.get()
                data_str = json.dumps(ev.model_dump())
                yield f"data: {data_str}\n\n"
        except asyncio.CancelledError:
            if q in log_queues:
                log_queues.remove(q)
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Mount static directory for frontend UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
