from typing import Any
from datetime import datetime
import uuid
from .registry import tool, ToolResult, ToolRisk
from ..memory.task_store import TaskStore

# Initialize task store
_task_store = TaskStore()

_tasks = ["create_task", "list_tasks", "complete_task", "reschedule_task", "list_overdue_tasks", "break_down_task", "extract_tasks_from_source", "note_to_task", "proactive_daily_plan", "smart_search", "capture_idea", "organize_inbox", "set_focus_mode", "get_daily_digest", "link_task_to_source", "batch_reschedule"]

@tool(name="create_task", category="tasks", risk=ToolRisk.LOW, description="Create a task with due date, priority, tags", reversible=True, idempotent=False, required_args=["title"])
async def create_task(title: str, description: str = "", due_date: str = None, priority: int = 1, tags: str = "") -> ToolResult:
    """Create a task with due date, priority, tags."""
    try:
        task_id = str(uuid.uuid4())
        await _task_store.create_task(
            task_id=task_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            tags=tags
        )
        return ToolResult(success=True, data={"task_id": task_id, "title": title})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="list_tasks", category="tasks", risk=ToolRisk.LOW, description="List/filter tasks (today, overdue, by tag)", reversible=True, idempotent=True)
async def list_tasks(status: str = None, tag: str = None) -> ToolResult:
    """List/filter tasks (today, overdue, by tag)."""
    try:
        tasks = await _task_store.get_tasks(status=status)
        if tag:
            tasks = [t for t in tasks if tag in t.get("tags", "")]
        return ToolResult(success=True, data=tasks)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="complete_task", category="tasks", risk=ToolRisk.LOW, description="Mark task done", reversible=False, idempotent=False, required_args=["task_id"])
async def complete_task(task_id: str) -> ToolResult:
    """Mark task done."""
    try:
        await _task_store.update_task_status(task_id, "completed")
        return ToolResult(success=True, data={"task_id": task_id, "status": "completed"})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="reschedule_task", category="tasks", risk=ToolRisk.MEDIUM, description="Move task to new date/time", reversible=True, idempotent=False, required_args=["task_id", "new_due_date"])
async def reschedule_task(task_id: str, new_due_date: str) -> ToolResult:
    """Move task to new date/time."""
    try:
        await _task_store._execute(
            "UPDATE tasks SET due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_due_date, task_id)
        )
        return ToolResult(success=True, data={"task_id": task_id, "new_due_date": new_due_date})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="list_overdue_tasks", category="tasks", risk=ToolRisk.LOW, description="Get all overdue items", reversible=True, idempotent=True)
async def list_overdue_tasks() -> ToolResult:
    """Get all overdue items."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE due_date < ? AND status != 'completed'",
            (today,)
        )
        return ToolResult(success=True, data=tasks)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="break_down_task", category="tasks", risk=ToolRisk.LOW, description="Split task into sub-steps (ADHD-friendly)", reversible=False, idempotent=False, required_args=["task_id", "subtasks"])
async def break_down_task(task_id: str, subtasks: list) -> ToolResult:
    """Split task into sub-steps (ADHD-friendly)."""
    try:
        subtask_dicts = []
        for i, st in enumerate(subtasks):
            subtask_id = str(uuid.uuid4())
            subtask_dicts.append({
                "id": subtask_id,
                "title": st if isinstance(st, str) else st.get("title", ""),
                "description": st.get("description", "") if isinstance(st, dict) else ""
            })
        
        await _task_store.break_down_task(task_id, subtask_dicts)
        return ToolResult(success=True, data={"parent_id": task_id, "subtasks": subtask_dicts})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="extract_tasks_from_source", category="tasks", risk=ToolRisk.LOW, description="Pull action items from email/note/file", reversible=True, idempotent=True, required_args=["source_text"])
async def extract_tasks_from_source(source_text: str) -> ToolResult:
    """Pull action items from email/note/file."""
    try:
        # Simple extraction - look for action items
        # In production, would use LLM for better extraction
        lines = source_text.split('\n')
        tasks = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line[0].isdigit()):
                tasks.append(line.lstrip('-*').lstrip('0123456789.').strip())
        
        return ToolResult(success=True, data={"extracted_tasks": tasks})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="note_to_task", category="tasks", risk=ToolRisk.LOW, description="Convert freeform note → structured todo", reversible=False, idempotent=False, required_args=["note"])
async def note_to_task(note: str, due_date: str = None) -> ToolResult:
    """Convert freeform note → structured todo."""
    try:
        task_id = str(uuid.uuid4())
        await _task_store.create_task(
            task_id=task_id,
            title=note[:100],  # First 100 chars as title
            description=note,
            due_date=due_date
        )
        return ToolResult(success=True, data={"task_id": task_id, "title": note[:100]})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="proactive_daily_plan", category="tasks", risk=ToolRisk.LOW, description="Scan inbox + calendar + tasks → today's plan", reversible=True, idempotent=True)
async def proactive_daily_plan() -> ToolResult:
    """Scan inbox + calendar + tasks → today's plan."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE due_date <= ? AND status != 'completed' ORDER BY priority DESC, due_date ASC",
            (today,)
        )
        
        plan = {
            "date": today,
            "total_tasks": len(tasks),
            "high_priority": len([t for t in tasks if t.get("priority", 0) >= 3]),
            "tasks": tasks[:10]  # Top 10 tasks
        }
        
        return ToolResult(success=True, data=plan)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="smart_search", category="tasks", risk=ToolRisk.LOW, description="Find where I wrote about X across all sources", reversible=True, idempotent=True, required_args=["query"])
async def smart_search(query: str) -> ToolResult:
    """Find where I wrote about X across all sources."""
    try:
        # Search tasks for matching titles/descriptions
        tasks = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE title LIKE ? OR description LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        
        # In production, would also search notes, documents, etc.
        return ToolResult(success=True, data={
            "query": query,
            "matches": tasks,
            "total_matches": len(tasks)
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="capture_idea", category="tasks", risk=ToolRisk.LOW, description="Quick inbox capture (voice/text/browser)", reversible=False, idempotent=False, required_args=["idea"])
async def capture_idea(idea: str, tags: str = "") -> ToolResult:
    """Quick inbox capture (voice/text/browser)."""
    try:
        task_id = str(uuid.uuid4())
        await _task_store.create_task(
            task_id=task_id,
            title=f"Idea: {idea[:50]}",
            description=idea,
            tags=f"inbox,{tags}" if tags else "inbox"
        )
        return ToolResult(success=True, data={"task_id": task_id, "idea": idea})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="organize_inbox", category="tasks", risk=ToolRisk.MEDIUM, description="Sort/triage captured ideas into categories", reversible=True, idempotent=False)
async def organize_inbox() -> ToolResult:
    """Sort/triage captured ideas into categories."""
    try:
        inbox_tasks = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE tags LIKE '%inbox%' AND status = 'pending'"
        )
        
        organized = {
            "total": len(inbox_tasks),
            "categories": {
                "quick_wins": [],
                "projects": [],
                "someday": [],
                "reference": []
            }
        }
        
        # Simple categorization based on content
        for task in inbox_tasks:
            title = task.get("title", "").lower()
            desc = task.get("description", "").lower()
            content = title + desc
            
            if any(kw in content for kw in ["quick", "simple", "easy", "fast"]):
                organized["categories"]["quick_wins"].append(task)
            elif any(kw in content for kw in ["project", "build", "create", "develop"]):
                organized["categories"]["projects"].append(task)
            elif any(kw in content for kw in ["someday", "maybe", "consider"]):
                organized["categories"]["someday"].append(task)
            else:
                organized["categories"]["reference"].append(task)
        
        return ToolResult(success=True, data=organized)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="set_focus_mode", category="tasks", risk=ToolRisk.LOW, description="Hide distractions, surface top 3 tasks", reversible=True, idempotent=True)
async def set_focus_mode() -> ToolResult:
    """Hide distractions, surface top 3 tasks."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE due_date <= ? AND status != 'completed' ORDER BY priority DESC LIMIT 3",
            (today,)
        )
        
        return ToolResult(success=True, data={
            "focus_tasks": tasks,
            "message": f"Focus mode: {len(tasks)} priority tasks surfaced"
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="get_daily_digest", category="tasks", risk=ToolRisk.LOW, description="End-of-day summary of done/pending", reversible=True, idempotent=True)
async def get_daily_digest() -> ToolResult:
    """End-of-day summary of done/pending."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        completed = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE status = 'completed' AND updated_at >= ?",
            (f"{today} 00:00:00",)
        )
        
        pending = await _task_store._fetchall(
            "SELECT * FROM tasks WHERE status != 'completed' AND due_date <= ?",
            (today,)
        )
        
        digest = {
            "date": today,
            "completed_count": len(completed),
            "completed_tasks": completed,
            "pending_count": len(pending),
            "pending_tasks": pending
        }
        
        return ToolResult(success=True, data=digest)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="link_task_to_source", category="tasks", risk=ToolRisk.LOW, description="Attach email/note URL to task", reversible=True, idempotent=False, required_args=["task_id", "source_url"])
async def link_task_to_source(task_id: str, source_url: str) -> ToolResult:
    """Attach email/note URL to task."""
    try:
        await _task_store._execute(
            "UPDATE tasks SET source_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (source_url, task_id)
        )
        return ToolResult(success=True, data={"task_id": task_id, "source_url": source_url})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="batch_reschedule", category="tasks", risk=ToolRisk.MEDIUM, description="Reschedule multiple overdue tasks at once", reversible=True, idempotent=False, required_args=["task_ids", "new_due_date"])
async def batch_reschedule(task_ids: list, new_due_date: str) -> ToolResult:
    """Reschedule multiple overdue tasks at once."""
    try:
        await _task_store.batch_reschedule(task_ids, new_due_date)
        return ToolResult(success=True, data={
            "task_ids": task_ids,
            "new_due_date": new_due_date,
            "count": len(task_ids)
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))
