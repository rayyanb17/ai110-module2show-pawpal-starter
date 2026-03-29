from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Dict, List, Optional


class TaskType(Enum):
	WALK = "walk"
	FEEDING = "feeding"
	MEDICATION = "medication"
	ENRICHMENT = "enrichment"
	GROOMING = "grooming"
	APPOINTMENT = "appointment"


class TaskStatus(Enum):
	PENDING = "pending"
	COMPLETED = "completed"
	SKIPPED = "skipped"


@dataclass
class Task:
	task_id: str
	title: str
	task_type: TaskType
	duration_minutes: int
	priority: int
	due_date: Optional[date] = None
	preferred_time: Optional[time] = None
	is_fixed_time: bool = False
	status: TaskStatus = TaskStatus.PENDING

	def set_preferred_time(self, task_time: time, is_fixed: bool = False) -> None:
		self.preferred_time = task_time
		self.is_fixed_time = is_fixed

	def mark_completed(self) -> None:
		self.status = TaskStatus.COMPLETED

	def is_overdue(self, now: datetime) -> bool:
		raise NotImplementedError


@dataclass
class Pet:
	pet_id: str
	name: str
	species: str
	age: int
	health_notes: str = ""
	tasks: List[Task] = field(default_factory=list)

	def add_task(self, task: Task) -> None:
		self.tasks.append(task)

	def remove_task(self, task_id: str) -> None:
		raise NotImplementedError

	def get_tasks_for_date(self, plan_date: date) -> List[Task]:
		raise NotImplementedError


@dataclass
class Owner:
	owner_id: str
	name: str
	preferences: Dict[str, str] = field(default_factory=dict)
	daily_available_minutes: int = 0
	pets: List[Pet] = field(default_factory=list)

	def add_pet(self, pet: Pet) -> None:
		self.pets.append(pet)

	def update_preferences(self, preferences: Dict[str, str]) -> None:
		self.preferences.update(preferences)


@dataclass
class ScheduledTask:
	task: Task
	start_time: datetime
	end_time: datetime
	reason: str = ""


@dataclass
class DailyPlan:
	plan_date: date
	items: List[ScheduledTask] = field(default_factory=list)
	unscheduled_tasks: List[Task] = field(default_factory=list)

	def add_item(self, item: ScheduledTask) -> None:
		self.items.append(item)

	def get_summary(self) -> str:
		raise NotImplementedError


@dataclass
class Scheduler:
	start_of_day: time = time(6, 0)
	end_of_day: time = time(22, 0)

	def create_daily_plan(self, owner: Owner, pet: Pet, plan_date: date) -> DailyPlan:
		raise NotImplementedError

	def prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
		raise NotImplementedError

	def place_fixed_time_tasks(self, tasks: List[Task]) -> List[ScheduledTask]:
		raise NotImplementedError

	def fill_remaining_slots(
		self,
		tasks: List[Task],
		occupied: List[ScheduledTask],
		plan_date: date,
	) -> List[ScheduledTask]:
		raise NotImplementedError


@dataclass
class PawPalSystem:
	owners: List[Owner] = field(default_factory=list)
	scheduler: Scheduler = field(default_factory=Scheduler)

	def add_owner(self, owner: Owner) -> None:
		self.owners.append(owner)

	def add_pet(self, owner_id: str, pet: Pet) -> None:
		raise NotImplementedError

	def add_task(self, pet_id: str, task: Task) -> None:
		raise NotImplementedError

	def generate_daily_plan(self, owner_id: str, pet_id: str, plan_date: date) -> DailyPlan:
		raise NotImplementedError
