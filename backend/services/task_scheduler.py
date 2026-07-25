"""
任务调度服务 - 核心调度逻辑，支持cron表达式和一次性定时任务。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from data.task_store import (
    create_task,
    delete_task,
    get_pending_tasks,
    get_task,
    list_tasks,
    update_task,
)
from models.schemas import (
    TaskDefinition,
    TaskRecord,
    TaskStatus,
    TaskType,
)

logger = logging.getLogger(__name__)

_scheduler_task: Optional[asyncio.Task] = None
_scheduler_running = False
_base_url = "http://localhost:8000"


def set_base_url(url: str) -> None:
    global _base_url
    _base_url = url


def _parse_cron_field(field: str, min_val: int, max_val: int) -> list[int]:
    if field == "*":
        return list(range(min_val, max_val + 1))
    values = []
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/")
            step = int(step)
            if base == "*":
                start = min_val
            else:
                start = int(base)
            values.extend(range(start, max_val + 1, step))
        elif "-" in part:
            start, end = part.split("-")
            values.extend(range(int(start), int(end) + 1))
        else:
            values.append(int(part))
    return sorted(set(v for v in values if min_val <= v <= max_val))


def _get_next_cron_time(cron_expr: str, after: datetime) -> Optional[datetime]:
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return None
        minute_field, hour_field, day_field, month_field, weekday_field = parts

        minutes = _parse_cron_field(minute_field, 0, 59)
        hours = _parse_cron_field(hour_field, 0, 23)
        days = _parse_cron_field(day_field, 1, 31)
        months = _parse_cron_field(month_field, 1, 12)
        weekdays = _parse_cron_field(weekday_field, 0, 6)

        candidate = after + timedelta(minutes=1)
        candidate = candidate.replace(second=0, microsecond=0)

        for _ in range(366 * 24 * 60):
            if candidate.month not in months:
                if candidate.month == 12:
                    candidate = candidate.replace(year=candidate.year + 1, month=1, day=1, hour=0, minute=0)
                else:
                    candidate = candidate.replace(month=candidate.month + 1, day=1, hour=0, minute=0)
                continue
            if candidate.day not in days:
                if candidate.day >= 28:
                    next_month = candidate.month + 1 if candidate.month < 12 else 1
                    next_year = candidate.year if candidate.month < 12 else candidate.year + 1
                    try:
                        candidate = candidate.replace(year=next_year, month=next_month, day=1, hour=0, minute=0)
                    except ValueError:
                        return None
                else:
                    candidate = candidate.replace(day=candidate.day + 1, hour=0, minute=0)
                continue
            if candidate.weekday() not in weekdays:
                candidate = candidate + timedelta(days=1)
                candidate = candidate.replace(hour=0, minute=0)
                continue
            if candidate.hour not in hours:
                if candidate.hour >= 23:
                    candidate = candidate + timedelta(days=1)
                    candidate = candidate.replace(hour=0, minute=0)
                else:
                    candidate = candidate.replace(hour=candidate.hour + 1, minute=0)
                continue
            if candidate.minute not in minutes:
                if candidate.minute >= 59:
                    if candidate.hour >= 23:
                        candidate = candidate + timedelta(days=1)
                        candidate = candidate.replace(hour=0, minute=0)
                    else:
                        candidate = candidate.replace(hour=candidate.hour + 1, minute=0)
                else:
                    candidate = candidate.replace(minute=candidate.minute + 1)
                continue
            return candidate
        return None
    except Exception as e:
        logger.error(f"解析cron表达式失败: {cron_expr}, 错误: {e}")
        return None


async def _execute_task(task: TaskRecord) -> None:
    logger.info(f"开始执行任务: {task.task_id} - {task.name}")
    update_task(task.task_id, status=TaskStatus.RUNNING, last_run_at=datetime.now(timezone.utc).isoformat())

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{_base_url}{task.target_endpoint}"
            response = await client.post(url, json=task.payload)
            result = response.json()
            if response.status_code == 200 and result.get("success", False):
                update_task(
                    task.task_id,
                    status=TaskStatus.COMPLETED if task.task_type == TaskType.ONCE else TaskStatus.PENDING,
                    last_result=result,
                    last_error="",
                    run_count=task.run_count + 1,
                )
                logger.info(f"任务执行成功: {task.task_id} - {task.name}")
            else:
                error_msg = result.get("message", f"HTTP {response.status_code}")
                update_task(
                    task.task_id,
                    status=TaskStatus.FAILED if task.task_type == TaskType.ONCE else TaskStatus.PENDING,
                    last_result=result,
                    last_error=error_msg,
                    run_count=task.run_count + 1,
                )
                logger.warning(f"任务执行失败: {task.task_id} - {task.name}, 错误: {error_msg}")
    except Exception as e:
        logger.error(f"任务执行异常: {task.task_id} - {task.name}, 错误: {e}")
        update_task(
            task.task_id,
            status=TaskStatus.FAILED if task.task_type == TaskType.ONCE else TaskStatus.PENDING,
            last_error=str(e),
            run_count=task.run_count + 1,
        )

    if task.task_type == TaskType.CRON:
        _schedule_next_cron_run(task.task_id)


def _schedule_next_cron_run(task_id: str) -> None:
    task = get_task(task_id)
    if not task or task.task_type != TaskType.CRON or not task.cron_expression:
        return
    now = datetime.now(timezone.utc)
    next_run = _get_next_cron_time(task.cron_expression, now)
    if next_run:
        update_task(task_id, next_run_at=next_run.isoformat())


async def _scheduler_loop() -> None:
    logger.info("任务调度器启动")
    while _scheduler_running:
        try:
            pending_tasks = get_pending_tasks()
            for task in pending_tasks:
                if task.status == TaskStatus.RUNNING:
                    continue
                asyncio.create_task(_execute_task(task))
        except Exception as e:
            logger.error(f"调度器循环异常: {e}")
        await asyncio.sleep(5)
    logger.info("任务调度器停止")


def start_scheduler() -> None:
    global _scheduler_task, _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    _scheduler_task = asyncio.create_task(_scheduler_loop())

    for task in list_tasks():
        if task.task_type == TaskType.CRON and task.status in (TaskStatus.PENDING, TaskStatus.PAUSED):
            _schedule_next_cron_run(task.task_id)


def stop_scheduler() -> None:
    global _scheduler_task, _scheduler_running
    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None


def create_scheduled_task(task_def: TaskDefinition) -> TaskRecord:
    task = create_task(task_def)
    if task.task_type == TaskType.CRON and task.cron_expression:
        now = datetime.now(timezone.utc)
        next_run = _get_next_cron_time(task.cron_expression, now)
        if next_run:
            update_task(task.task_id, next_run_at=next_run.isoformat())
    return task


def trigger_task(task_id: str) -> Optional[TaskRecord]:
    task = get_task(task_id)
    if not task:
        return None
    asyncio.create_task(_execute_task(task))
    return task


def pause_task(task_id: str) -> Optional[TaskRecord]:
    task = get_task(task_id)
    if not task:
        return None
    if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
        update_task(task_id, status=TaskStatus.PAUSED)
    return get_task(task_id)


def resume_task(task_id: str) -> Optional[TaskRecord]:
    task = get_task(task_id)
    if not task:
        return None
    if task.status == TaskStatus.PAUSED:
        if task.task_type == TaskType.CRON:
            _schedule_next_cron_run(task_id)
        update_task(task_id, status=TaskStatus.PENDING)
    return get_task(task_id)


def remove_task(task_id: str) -> bool:
    return delete_task(task_id)


def get_scheduler_status() -> dict:
    tasks = list_tasks()
    return {
        "running": _scheduler_running,
        "total_tasks": len(tasks),
        "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
        "running_count": len([t for t in tasks if t.status == TaskStatus.RUNNING]),
        "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
        "paused": len([t for t in tasks if t.status == TaskStatus.PAUSED]),
        "cancelled": len([t for t in tasks if t.status == TaskStatus.CANCELLED]),
    }
