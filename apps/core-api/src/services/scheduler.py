"""Scheduler service implementation using APScheduler."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling and managing periodic tasks."""
    
    def __init__(
        self,
        timezone: str = "UTC",
        job_defaults: Optional[Dict[str, Any]] = None,
        max_instances: int = 3,
        coalesce: bool = True,
        misfire_grace_time: int = 30,
    ):
        self.timezone = timezone
        self.job_defaults = job_defaults or {
            "coalesce": coalesce,
            "max_instances": max_instances,
            "misfire_grace_time": misfire_grace_time,
        }
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._job_registry: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self) -> None:
        """Initialize the scheduler."""
        try:
            logger.info("Initializing scheduler service")
            
            # Configure job stores and executors
            jobstores = {
                "default": MemoryJobStore()
            }
            
            executors = {
                "default": AsyncIOExecutor()
            }
            
            # Create scheduler
            self._scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=self.job_defaults,
                timezone=self.timezone
            )
            
            # Start scheduler
            self._scheduler.start()
            
            logger.info("Scheduler service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        **options
    ) -> Job:
        """Add a job that runs at fixed intervals."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        if not any([seconds, minutes, hours, days]):
            raise ValueError("At least one time interval must be specified")
        
        try:
            # Create interval trigger
            trigger = IntervalTrigger(
                seconds=seconds or 0,
                minutes=minutes or 0,
                hours=hours or 0,
                days=days or 0,
                start_date=start_date,
                end_date=end_date,
                timezone=self.timezone
            )
            
            # Add job
            job = self._scheduler.add_job(
                func,
                trigger,
                id=job_id,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True,
                **options
            )
            
            # Register job
            self._job_registry[job_id] = {
                "type": "interval",
                "func": func.__name__,
                "trigger": {
                    "seconds": seconds,
                    "minutes": minutes,
                    "hours": hours,
                    "days": days,
                },
                "created_at": datetime.utcnow(),
            }
            
            logger.info(f"Added interval job: {job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to add interval job {job_id}: {e}")
            raise
    
    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        year: Optional[Union[int, str]] = None,
        month: Optional[Union[int, str]] = None,
        day: Optional[Union[int, str]] = None,
        week: Optional[Union[int, str]] = None,
        day_of_week: Optional[Union[int, str]] = None,
        hour: Optional[Union[int, str]] = None,
        minute: Optional[Union[int, str]] = None,
        second: Optional[Union[int, str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        **options
    ) -> Job:
        """Add a job that runs based on cron expression."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            # Create cron trigger
            trigger = CronTrigger(
                year=year,
                month=month,
                day=day,
                week=week,
                day_of_week=day_of_week,
                hour=hour,
                minute=minute,
                second=second,
                start_date=start_date,
                end_date=end_date,
                timezone=self.timezone
            )
            
            # Add job
            job = self._scheduler.add_job(
                func,
                trigger,
                id=job_id,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True,
                **options
            )
            
            # Register job
            self._job_registry[job_id] = {
                "type": "cron",
                "func": func.__name__,
                "trigger": {
                    "year": year,
                    "month": month,
                    "day": day,
                    "week": week,
                    "day_of_week": day_of_week,
                    "hour": hour,
                    "minute": minute,
                    "second": second,
                },
                "created_at": datetime.utcnow(),
            }
            
            logger.info(f"Added cron job: {job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to add cron job {job_id}: {e}")
            raise
    
    def add_date_job(
        self,
        job_id: str,
        func: Callable,
        run_date: datetime,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        **options
    ) -> Job:
        """Add a job that runs once at a specific date/time."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            # Create date trigger
            trigger = DateTrigger(
                run_date=run_date,
                timezone=self.timezone
            )
            
            # Add job
            job = self._scheduler.add_job(
                func,
                trigger,
                id=job_id,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True,
                **options
            )
            
            # Register job
            self._job_registry[job_id] = {
                "type": "date",
                "func": func.__name__,
                "trigger": {
                    "run_date": run_date.isoformat(),
                },
                "created_at": datetime.utcnow(),
            }
            
            logger.info(f"Added date job: {job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to add date job {job_id}: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        return self._scheduler.get_job(job_id)
    
    def get_jobs(self) -> List[Job]:
        """Get all scheduled jobs."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        return self._scheduler.get_jobs()
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            self._scheduler.remove_job(job_id)
            
            # Remove from registry
            if job_id in self._job_registry:
                del self._job_registry[job_id]
            
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def modify_job(
        self,
        job_id: str,
        **changes
    ) -> bool:
        """Modify job properties."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            self._scheduler.modify_job(job_id, **changes)
            logger.info(f"Modified job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to modify job {job_id}: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed job status."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        job = self.get_job(job_id)
        if not job:
            return None
        
        registry_info = self._job_registry.get(job_id, {})
        
        return {
            "id": job.id,
            "name": job.name,
            "func": job.func_ref,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending,
            "coalesce": job.coalesce,
            "max_instances": job.max_instances,
            "misfire_grace_time": job.misfire_grace_time,
            "registry_info": registry_info,
        }
    
    def get_all_job_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all jobs."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        return [
            self.get_job_status(job.id)
            for job in self.get_jobs()
            if self.get_job_status(job.id)
        ]
    
    async def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler service shut down")
    
    async def close(self) -> None:
        """Alias for shutdown."""
        await self.shutdown()