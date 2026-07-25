"""
任务存储层 - 管理调度任务的持久化存储。
当前使用内存存储，生产环境可替换为数据库。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from models.schemas import (
    TaskDefinition,
    TaskRecord,
    TaskStatus,
    TaskType,
)


_tasks: dict[str, TaskRecord] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_task(task_def: TaskDefinition) -> TaskRecord:
    task_id = str(uuid.uuid4())
    now = _now_iso()
    next_run = ""
    if task_def.task_type == TaskType.ONCE and task_def.run_at:
        next_run = task_def.run_at

    record = TaskRecord(
        task_id=task_id,
        name=task_def.name,
        task_type=task_def.task_type,
        cron_expression=task_def.cron_expression,
        run_at=task_def.run_at,
        target_endpoint=task_def.target_endpoint,
        payload=task_def.payload,
        description=task_def.description,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
        next_run_at=next_run,
    )
    _tasks[task_id] = record
    return record


def get_task(task_id: str) -> Optional[TaskRecord]:
    return _tasks.get(task_id)


def list_tasks(status: Optional[TaskStatus] = None) -> list[TaskRecord]:
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t.status == status]
    return sorted(tasks, key=lambda t: t.created_at, reverse=True)


def update_task(task_id: str, **kwargs) -> Optional[TaskRecord]:
    task = _tasks.get(task_id)
    if not task:
        return None
    update_data = task.model_dump()
    for key, value in kwargs.items():
        if value is not None and hasattr(task, key):
            update_data[key] = value
    update_data["updated_at"] = _now_iso()
    updated = TaskRecord(**update_data)
    _tasks[task_id] = updated
    return updated


def delete_task(task_id: str) -> bool:
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def get_pending_tasks() -> list[TaskRecord]:
    now = datetime.now(timezone.utc)
    pending = []
    for task in _tasks.values():
        if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            continue
        if task.task_type == TaskType.ONCE and task.run_at:
            try:
                run_time = datetime.fromisoformat(task.run_at.replace("Z", "+00:00"))
                if run_time <= now:
                    pending.append(task)
            except ValueError:
                continue
        elif task.task_type == TaskType.CRON and task.next_run_at:
            try:
                next_run = datetime.fromisoformat(task.next_run_at.replace("Z", "+00:00"))
                if next_run <= now:
                    pending.append(task)
            except ValueError:
                continue
    return pending


def get_tasks_count() -> int:
    return len(_tasks)
