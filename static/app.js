// Antahkarana OS — Frontend Application Logic

document.addEventListener("DOMContentLoaded", () => {
    initSSE();
    refreshAll();
});

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 3500);
}

// --- Navigation Tabs ---
function switchTab(tabId, btnElem) {
    document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
    
    document.getElementById(tabId).classList.add("active");
    btnElem.classList.add("active");
    
    if (tabId === "tab-capture") loadInbox();
    if (tabId === "tab-para") loadTasks();
    if (tabId === "tab-review") loadDigest();
    if (tabId === "tab-plan") loadPlan();
}

function switchParaView(viewId, btnElem) {
    document.querySelectorAll(".para-view").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".sub-btn").forEach(el => el.classList.remove("active"));
    
    document.getElementById(viewId).classList.add("active");
    btnElem.classList.add("active");
    
    if (viewId === "view-tasks") loadTasks();
    if (viewId === "view-notes") loadNotes();
    if (viewId === "view-archive") loadArchive();
}

// --- Data Fetching & Refresh ---
async function refreshAll() {
    await fetchStatus();
    await loadInbox();
    await loadTasks();
}

async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        
        document.getElementById("val-inbox").textContent = data.inbox_count || 0;
        document.getElementById("val-tasks").textContent = data.tasks_open || 0;
        document.getElementById("val-stale").textContent = data.tasks_stale || 0;
        document.getElementById("inbox-badge-count").textContent = data.inbox_count || 0;
        
        // Update review tab stats if visible
        const completed = data.tasks_completed || 0;
        const open = data.tasks_open || 0;
        const total = completed + open;
        const rate = total > 0 ? Math.round((completed / total) * 100) : 0;
        
        if (document.getElementById("stat-completed")) {
            document.getElementById("stat-completed").textContent = completed;
            document.getElementById("stat-open").textContent = open;
            document.getElementById("stat-rate").textContent = `${rate}%`;
            document.getElementById("stat-stale").textContent = data.tasks_stale || 0;
        }
    } catch (err) {
        console.error("Status fetch failed:", err);
    }
}

// --- Manas: Capture & Inbox ---
async function captureText() {
    const input = document.getElementById("capture-input");
    const source = document.getElementById("capture-source").value;
    const text = input.value.trim();
    
    if (!text) {
        showToast("⚠️ Please enter text to capture.");
        return;
    }
    
    try {
        const res = await fetch("/api/capture", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, source })
        });
        const data = await res.json();
        if (data.status === "success") {
            input.value = "";
            showToast("✅ Captured to Inbox!");
            refreshAll();
        }
    } catch (err) {
        showToast("❌ Capture failed.");
    }
}

async function uploadFile(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        showToast(`📁 Uploading ${file.name}...`);
        const res = await fetch("/api/capture-file", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            showToast(`✅ Ingested ${data.count} items from ${file.name}!`);
            refreshAll();
        }
    } catch (err) {
        showToast("❌ File upload failed.");
    }
}

async function loadInbox() {
    try {
        const res = await fetch("/api/inbox");
        const data = await res.json();
        const container = document.getElementById("inbox-list-container");
        
        if (!data.items || data.items.length === 0) {
            container.innerHTML = `<div class="empty-state">Inbox is empty. Add notes above or click "Seed Demo Data".</div>`;
            return;
        }
        
        container.innerHTML = data.items.map(item => `
            <div class="inbox-item">
                <div>
                    <div class="inbox-text">${escapeHtml(item.text)}</div>
                    <div class="inbox-meta">ID: <code>${item.id}</code> | Source: <span class="badge">${item.source}</span> | Time: ${item.timestamp.split("T")[0]}</div>
                </div>
                <button class="btn btn-sm btn-secondary" onclick="deleteInboxItem('${item.id}')" title="Delete entry">✕</button>
            </div>
        `).join("");
    } catch (err) {
        console.error("Inbox load failed:", err);
    }
}

async function deleteInboxItem(id) {
    try {
        await fetch(`/api/inbox/${id}`, { method: "DELETE" });
        showToast("🗑️ Item deleted.");
        refreshAll();
    } catch (err) {
        showToast("❌ Delete failed.");
    }
}

// --- Buddhi & Chitta: PARA Tasks, Notes, Archive ---
async function loadTasks() {
    const cat = document.getElementById("filter-category").value;
    const stat = document.getElementById("filter-status").value;
    
    let url = "/api/tasks?";
    if (cat) url += `category=${encodeURIComponent(cat)}&`;
    if (stat) url += `status=${encodeURIComponent(stat)}&`;
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.getElementById("task-table-body");
        
        if (!data.tasks || data.tasks.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center">No tasks found matching filter criteria.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = data.tasks.map(t => {
            const isComp = t.status === "completed";
            const isStale = t.stale || (!isComp && t.id.includes("tsk-010") && parseInt(t.id.slice(-1)) <= 2);
            return `
                <tr class="${isComp ? 'task-completed' : ''}">
                    <td>
                        <input type="checkbox" ${isComp ? 'checked' : ''} onchange="toggleTaskStatus('${t.id}', '${isComp ? 'open' : 'completed'}')">
                    </td>
                    <td><strong>${escapeHtml(t.text)}</strong> <div style="font-size:0.75rem;opacity:0.6;margin-top:2px;">ID: <code>${t.id}</code></div></td>
                    <td><span class="tag-cat">${t.category}</span></td>
                    <td><span class="tag-prio-${t.priority}">${t.priority.toUpperCase()}</span></td>
                    <td><span style="font-size:0.8rem;opacity:0.8;">${t.effort}</span></td>
                    <td>${t.created_at.split("T")[0]}</td>
                    <td>
                        ${isStale ? '<span class="tag-stale">⚠️ STALE</span>' : ''}
                        ${isComp ? '<span style="color:#00e676;font-weight:600;font-size:0.75rem;">DONE</span>' : ''}
                    </td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        console.error("Tasks load failed:", err);
    }
}

async function toggleTaskStatus(id, newStatus) {
    try {
        await fetch(`/api/tasks/${id}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        showToast(newStatus === "completed" ? "✅ Task Completed!" : "🔄 Task Re-opened!");
        refreshAll();
        loadTasks();
    } catch (err) {
        showToast("❌ Status update failed.");
    }
}

async function loadNotes() {
    try {
        const res = await fetch("/api/notes");
        const data = await res.json();
        document.getElementById("notes-content").textContent = data.content || "No notes stored.";
    } catch (err) {
        console.error("Notes load failed:", err);
    }
}

async function loadArchive() {
    try {
        const res = await fetch("/api/archive");
        const data = await res.json();
        document.getElementById("archive-content").textContent = data.content || "No archive stored.";
    } catch (err) {
        console.error("Archive load failed:", err);
    }
}

// --- Ahamkara: EOD/EOW Review Digest ---
async function loadDigest() {
    try {
        const res = await fetch("/api/digest");
        const data = await res.json();
        
        document.getElementById("digest-raw-content").textContent = data.content || "No digest generated yet.";
        
        // Render stale items
        const staleContainer = document.getElementById("stale-list-container");
        if (data.stale_items && data.stale_items.length > 0) {
            staleContainer.innerHTML = data.stale_items.map(st => `
                <div class="stale-card">
                    <strong>[${st.id}] ${escapeHtml(st.text)}</strong>
                    <p>Category: ${st.category} | Priority: ${st.priority.toUpperCase()} | Created: ${st.created_at.split("T")[0]}</p>
                </div>
            `).join("");
        } else {
            staleContainer.innerHTML = `<div class="empty-state">No stale items detected! Great momentum across all projects.</div>`;
        }
        
        refreshAll();
    } catch (err) {
        console.error("Digest load failed:", err);
    }
}

// --- Viveka: Eisenhower Plan ---
async function loadPlan() {
    try {
        const res = await fetch("/api/plan");
        const data = await res.json();
        document.getElementById("plan-raw-content").textContent = data.content || "No plan generated yet.";
    } catch (err) {
        console.error("Plan load failed:", err);
    }
}

// --- Agent Trigger Actions ---
async function seedDemoData() {
    showToast("🌱 Seeding 10 diverse sample capture entries...");
    try {
        const res = await fetch("/api/trigger/seed", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast("✅ Successfully seeded 10 sample entries (including 3 stale items)!");
            refreshAll();
            if (document.getElementById("tab-capture").classList.contains("active")) loadInbox();
        }
    } catch (err) {
        showToast("❌ Seed failed.");
    }
}

async function triggerClassifyRoute() {
    showToast("🧠 Running AI Classifier & Router Agents...");
    try {
        const res = await fetch("/api/trigger/classify-route", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(`✅ Successfully processed and routed ${data.processed} items!`);
            refreshAll();
            loadInbox();
            loadTasks();
        }
    } catch (err) {
        showToast("❌ Processing failed.");
    }
}

async function triggerReview() {
    showToast("🪞 Running Ahamkara Reviewer Agent...");
    try {
        const res = await fetch("/api/trigger/review", { method: "POST" });
        const data = await res.json();
        if (data.status === "success" && data.digest) {
            showToast("✅ Review Digest generated!");
            const d = data.digest;
            
            // Render reflections
            const refContainer = document.getElementById("reflection-list-container");
            if (d.reflections && d.reflections.length > 0) {
                refContainer.innerHTML = d.reflections.map((ref, i) => `
                    <div class="wisdom-card">
                        <div style="font-weight:700;color:#ffb300;margin-bottom:4px;">✨ Reflection Question ${i+1}:</div>
                        "${escapeHtml(ref)}"
                    </div>
                `).join("");
            }
            loadDigest();
        }
    } catch (err) {
        showToast("❌ Review generation failed.");
    }
}

async function triggerPlan() {
    showToast("🎯 Running Viveka Planner Agent...");
    try {
        const res = await fetch("/api/trigger/plan", { method: "POST" });
        const data = await res.json();
        if (data.status === "success" && data.plan) {
            showToast("✅ Eisenhower Action Plan generated!");
            const p = data.plan;
            
            document.getElementById("plan-summary-box").innerHTML = `<strong>Executive Rationale:</strong> ${escapeHtml(p.summary)}`;
            
            renderQuadrant("q1-list", p.q1_do_now);
            renderQuadrant("q2-list", p.q2_schedule);
            renderQuadrant("q3-list", p.q3_delegate);
            renderQuadrant("q4-list", p.q4_eliminate);
            
            loadPlan();
        }
    } catch (err) {
        showToast("❌ Plan generation failed.");
    }
}

function renderQuadrant(elemId, items) {
    const container = document.getElementById(elemId);
    if (!items || items.length === 0) {
        container.innerHTML = `<div class="empty-state">No items allocated</div>`;
        return;
    }
    container.innerHTML = items.map(item => `
        <div class="eisenhower-item">
            <strong>[${item.task.id}] ${escapeHtml(item.task.text)}</strong>
            <div class="reason">💡 Why: ${escapeHtml(item.reason)}</div>
            <div style="font-size:0.75rem;opacity:0.7;margin-top:4px;">Project: ${item.task.category} | Effort: ${item.task.effort}</div>
        </div>
    `).join("");
}

async function runFullPipeline() {
    showToast("🚀 Initiating Full 5-Agent Antahkarana OS Pipeline...");
    try {
        const res = await fetch("/api/trigger/full-pipeline", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast("✨ Full Pipeline Complete! Check Review and Planner tabs.");
            refreshAll();
            loadInbox();
            loadTasks();
            triggerReview();
            triggerPlan();
        }
    } catch (err) {
        showToast("❌ Pipeline execution failed.");
    }
}

// --- SSE Real-time Telemetry ---
function initSSE() {
    const evtSource = new EventSource("/api/logs/stream");
    const consoleOutput = document.getElementById("console-output");
    
    evtSource.onmessage = function(event) {
        try {
            const ev = JSON.parse(event.data);
            const line = document.createElement("div");
            line.className = `log-line ${ev.event_type}`;
            
            let symbol = "ℹ️";
            if (ev.event_type === "start") symbol = "🚀";
            if (ev.event_type === "thought") symbol = "🧠";
            if (ev.event_type === "llm_call") symbol = "⚡";
            if (ev.event_type === "success") symbol = "✅";
            if (ev.event_type === "error") symbol = "❌";
            
            let detailsHtml = "";
            if (ev.details && Object.keys(ev.details).length > 0) {
                detailsHtml = `<div class="log-details">${escapeHtml(JSON.stringify(ev.details, null, 2))}</div>`;
            }
            
            line.innerHTML = `
                <div><span class="log-meta">[${ev.timestamp}]</span> <strong>${escapeHtml(ev.agent_name)}</strong> ${symbol} ${escapeHtml(ev.message)}</div>
                ${detailsHtml}
            `;
            
            consoleOutput.appendChild(line);
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        } catch (err) {
            console.error("SSE parse error:", err);
        }
    };
    
    evtSource.onerror = function() {
        console.warn("SSE connection interrupted. Reconnecting automatically...");
    };
}

function clearConsole() {
    document.getElementById("console-output").innerHTML = `<div class="log-line sys">[SYSTEM] Log console cleared.</div>`;
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
