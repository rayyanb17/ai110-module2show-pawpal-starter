from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import uuid4


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


class TaskRecurrence(Enum):
	NONE = "none"
	DAILY = "daily"
	WEEKLY = "weekly"


@dataclass
class Task:
	title: str
	task_type: TaskType
	duration_minutes: int
	priority: int
	due_date: Optional[date] = None
	preferred_time: Optional[time] = None
	is_fixed_time: bool = False
	recurrence: TaskRecurrence = TaskRecurrence.NONE
	status: TaskStatus = TaskStatus.PENDING
	task_id: str = field(default_factory=lambda: f"task-{uuid4().hex[:8]}")

	def __post_init__(self) -> None:
		"""Ensure every task has a non-empty unique identifier."""
		if not self.task_id:
			self.task_id = f"task-{uuid4().hex[:8]}"

	def set_preferred_time(self, task_time: time, is_fixed: bool = False) -> None:
		"""Set the preferred time and whether the time is fixed."""
		self.preferred_time = task_time
		self.is_fixed_time = is_fixed

	def mark_completed(self) -> None:
		"""Mark this task as completed."""
		self.status = TaskStatus.COMPLETED

	def next_due_date(self, completed_on: date) -> Optional[date]:
		"""Calculate the next due date for recurring tasks."""
		if self.recurrence == TaskRecurrence.NONE:
			return None

		base_date = completed_on
		if self.recurrence == TaskRecurrence.DAILY:
			return base_date + timedelta(days=1)
		if self.recurrence == TaskRecurrence.WEEKLY:
			return base_date + timedelta(days=7)
		return None

	def is_overdue(self, now: datetime) -> bool:
		"""Return True when the task is pending and past its due moment."""
		if self.status == TaskStatus.COMPLETED:
			return False

		if self.due_date is None:
			return False

		if now.date() > self.due_date:
			return True

		if now.date() == self.due_date and self.preferred_time is not None:
			return now.time() > self.preferred_time

		return False


@dataclass
class Pet:
	pet_id: str
	name: str
	species: str
	age: int
	health_notes: str = ""
	tasks: List[Task] = field(default_factory=list)

	def add_task(self, task: Task) -> None:
		"""Add a task to this pet's task list."""
		self.tasks.append(task)

	def remove_task(self, task_id: str) -> None:
		"""Remove a task by ID or raise an error when not found."""
		for index, task in enumerate(self.tasks):
			if task.task_id == task_id:
				del self.tasks[index]
				return
		raise ValueError(f"Task not found: {task_id}")

	def get_tasks_for_date(self, plan_date: date) -> List[Task]:
		"""Return pending tasks due on or before the given date."""
		result: List[Task] = []
		for task in self.tasks:
			if task.status == TaskStatus.COMPLETED:
				continue
			if task.due_date is None or task.due_date <= plan_date:
				result.append(task)
		return result


@dataclass
class Owner:
	owner_id: str
	name: str
	preferences: Dict[str, str] = field(default_factory=dict)
	daily_available_minutes: int = 0
	pets: List[Pet] = field(default_factory=list)

	def add_pet(self, pet: Pet) -> None:
		"""Attach a pet to this owner."""
		self.pets.append(pet)

	def update_preferences(self, preferences: Dict[str, str]) -> None:
		"""Merge new preference values into the owner's preferences."""
		self.preferences.update(preferences)


@dataclass
class ScheduledTask:
	task: Task
	start_time: datetime
	end_time: datetime
	reason: str = ""
	pet_names: List[str] = field(default_factory=list)


@dataclass
class TaskCandidate:
	task: Task
	pet_names: List[str]
	source_tasks: List[Task]


@dataclass
class DailyPlan:
	plan_date: date
	items: List[ScheduledTask] = field(default_factory=list)
	unscheduled_tasks: List[Task] = field(default_factory=list)
	conflicts: List[str] = field(default_factory=list)

	def add_item(self, item: ScheduledTask) -> None:
		"""Append a scheduled task item to the daily plan."""
		self.items.append(item)

	def get_summary(self) -> str:
		"""Build a compact text summary for the daily plan."""
		scheduled_count = len(self.items)
		unscheduled_count = len(self.unscheduled_tasks)
		total_minutes = 0
		for scheduled in self.items:
			total_minutes += scheduled.task.duration_minutes

		summary = (
			f"Plan for {self.plan_date.isoformat()}: "
			f"{scheduled_count} scheduled tasks, "
			f"{unscheduled_count} unscheduled, "
			f"{total_minutes} total scheduled minutes."
		)

		if unscheduled_count:
			unscheduled_titles = ", ".join(task.title for task in self.unscheduled_tasks)
			summary += f" Unscheduled: {unscheduled_titles}."

		if self.conflicts:
			summary += f" Conflicts detected: {len(self.conflicts)}."

		return summary


@dataclass
class Scheduler:
	start_of_day: time = time(6, 0)
	end_of_day: time = time(22, 0)

	def create_daily_plan(self, owner: Owner, pet: Pet, plan_date: date) -> DailyPlan:
		"""Generate a daily plan for one pet using owner constraints."""
		candidates = [
			TaskCandidate(task=task, pet_names=[pet.name], source_tasks=[task])
			for task in pet.get_tasks_for_date(plan_date)
		]
		return self._create_plan_for_candidates(owner=owner, candidates=candidates, plan_date=plan_date)

	def create_owner_daily_plan(self, owner: Owner, plan_date: date) -> DailyPlan:
		"""Generate one schedule across all of an owner's pets."""
		candidates: List[TaskCandidate] = []
		for pet in owner.pets:
			for task in pet.get_tasks_for_date(plan_date):
				candidates.append(TaskCandidate(task=task, pet_names=[pet.name], source_tasks=[task]))

		if not candidates:
			return DailyPlan(plan_date=plan_date)

		normalized = self._merge_walk_candidates(candidates, plan_date)
		return self._create_plan_for_candidates(owner=owner, candidates=normalized, plan_date=plan_date)

	def _create_plan_for_candidates(self, owner: Owner, candidates: List[TaskCandidate], plan_date: date) -> DailyPlan:
		"""Schedule candidate tasks while tracking original source tasks and pet names."""
		plan = DailyPlan(plan_date=plan_date)

		if not candidates:
			return plan

		day_start, day_end = self._resolve_day_bounds(owner, plan_date)
		prioritized = self.prioritize_candidates(candidates)

		fixed_candidates = [
			candidate
			for candidate in prioritized
			if candidate.task.is_fixed_time and candidate.task.preferred_time is not None
		]
		flex_candidates = [candidate for candidate in prioritized if candidate not in fixed_candidates]

		fixed_scheduled, invalid_fixed = self.place_fixed_time_candidates(
			candidates=fixed_candidates,
			plan_date=plan_date,
			day_start=day_start,
			day_end=day_end,
		)
		plan.items.extend(fixed_scheduled)
		for candidate in invalid_fixed:
			plan.unscheduled_tasks.extend(candidate.source_tasks)

		remaining_minutes = max(owner.daily_available_minutes, 0)
		for scheduled in fixed_scheduled:
			remaining_minutes -= scheduled.task.duration_minutes

		if remaining_minutes <= 0:
			for candidate in flex_candidates:
				plan.unscheduled_tasks.extend(candidate.source_tasks)
			plan.items.sort(key=lambda item: item.start_time)
			plan.conflicts = self.detect_time_conflicts(plan.items)
			return plan

		flex_scheduled, flex_unscheduled = self.fill_remaining_slots(
			candidates=flex_candidates,
			occupied=fixed_scheduled,
			plan_date=plan_date,
			day_start=day_start,
			day_end=day_end,
			available_minutes=remaining_minutes,
		)

		plan.items.extend(flex_scheduled)
		for candidate in flex_unscheduled:
			plan.unscheduled_tasks.extend(candidate.source_tasks)
		plan.items.sort(key=lambda item: item.start_time)
		plan.conflicts = self.detect_time_conflicts(plan.items)
		return plan

	def detect_time_conflicts(self, scheduled_items: List[ScheduledTask]) -> List[str]:
		"""Detect overlapping tasks, except overlaps where both tasks are walks."""
		conflicts: List[str] = []
		ordered = sorted(scheduled_items, key=lambda item: item.start_time)

		for index, left in enumerate(ordered):
			for right in ordered[index + 1 :]:
				if right.start_time >= left.end_time:
					break

				if left.task.task_type == TaskType.WALK and right.task.task_type == TaskType.WALK:
					continue

				left_pets = ", ".join(left.pet_names) if left.pet_names else "Unknown pet"
				right_pets = ", ".join(right.pet_names) if right.pet_names else "Unknown pet"
				conflicts.append(
					f"{left.start_time.strftime('%H:%M')}-{left.end_time.strftime('%H:%M')} "
					f"{left.task.title} [{left_pets}] overlaps with "
					f"{right.start_time.strftime('%H:%M')}-{right.end_time.strftime('%H:%M')} "
					f"{right.task.title} [{right_pets}]"
				)

		return conflicts

	def prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
		"""Sort tasks by fixed-time status, due date, priority, and length."""
		return sorted(tasks, key=self._task_sort_key)

	def prioritize_candidates(self, candidates: List[TaskCandidate]) -> List[TaskCandidate]:
		"""Sort candidates by task urgency and scheduling constraints."""
		return sorted(candidates, key=lambda candidate: self._task_sort_key(candidate.task))

	def _task_sort_key(self, task: Task) -> Tuple[bool, date, int, int, str]:
		"""Return a sortable key that keeps scheduling priorities deterministic."""
		due_sort_value = task.due_date if task.due_date is not None else date.max
		return (
			not task.is_fixed_time,
			due_sort_value,
			-task.priority,
			task.duration_minutes,
			task.title.lower(),
		)

	def _merge_walk_candidates(self, candidates: List[TaskCandidate], plan_date: date) -> List[TaskCandidate]:
		"""Merge compatible walk tasks so multiple pets can be walked together."""
		walk_candidates: List[TaskCandidate] = []
		non_walk_candidates: List[TaskCandidate] = []

		for candidate in candidates:
			if candidate.task.task_type == TaskType.WALK:
				walk_candidates.append(candidate)
			else:
				non_walk_candidates.append(candidate)

		if not walk_candidates:
			return candidates

		fixed_groups: Dict[time, List[TaskCandidate]] = {}
		flex_group: List[TaskCandidate] = []

		for candidate in walk_candidates:
			task = candidate.task
			if task.is_fixed_time and task.preferred_time is not None:
				fixed_groups.setdefault(task.preferred_time, []).append(candidate)
			else:
				flex_group.append(candidate)

		merged: List[TaskCandidate] = list(non_walk_candidates)
		for preferred_time in sorted(fixed_groups.keys()):
			group = fixed_groups[preferred_time]
			merged.append(self._merge_walk_group(group=group, plan_date=plan_date, is_fixed=True))

		if flex_group:
			merged.append(self._merge_walk_group(group=flex_group, plan_date=plan_date, is_fixed=False))

		return merged

	def _merge_walk_group(self, group: List[TaskCandidate], plan_date: date, is_fixed: bool) -> TaskCandidate:
		"""Create one combined walk candidate from multiple pet walk tasks."""
		pet_names = sorted({name for candidate in group for name in candidate.pet_names})
		preferred_times = [candidate.task.preferred_time for candidate in group if candidate.task.preferred_time is not None]
		due_dates = [candidate.task.due_date for candidate in group if candidate.task.due_date is not None]

		combined_task = Task(
			title=f"Walk ({', '.join(pet_names)})",
			task_type=TaskType.WALK,
			duration_minutes=max(candidate.task.duration_minutes for candidate in group),
			priority=max(candidate.task.priority for candidate in group),
			due_date=min(due_dates) if due_dates else plan_date,
			preferred_time=min(preferred_times) if preferred_times else None,
			is_fixed_time=is_fixed,
		)

		source_tasks: List[Task] = []
		for candidate in group:
			source_tasks.extend(candidate.source_tasks)

		return TaskCandidate(task=combined_task, pet_names=pet_names, source_tasks=source_tasks)

	def place_fixed_time_candidates(
		self,
		candidates: List[TaskCandidate],
		plan_date: date,
		day_start: datetime,
		day_end: datetime,
	) -> Tuple[List[ScheduledTask], List[TaskCandidate]]:
		"""Schedule fixed-time tasks and return both scheduled and rejected tasks."""
		scheduled: List[ScheduledTask] = []
		unscheduled: List[TaskCandidate] = []

		ordered = sorted(
			candidates,
			key=lambda candidate: (
				candidate.task.preferred_time or time(23, 59),
				-candidate.task.priority,
			),
		)

		for candidate in ordered:
			task = candidate.task
			if task.preferred_time is None:
				unscheduled.append(candidate)
				continue

			start_dt = datetime.combine(plan_date, task.preferred_time)
			end_dt = start_dt + timedelta(minutes=task.duration_minutes)

			if start_dt < day_start or end_dt > day_end:
				unscheduled.append(candidate)
				continue

			if self._has_overlap(start_dt, end_dt, scheduled):
				unscheduled.append(candidate)
				continue

			reason = self._reason_for_task(task=task, start_dt=start_dt, pet_names=candidate.pet_names)
			scheduled.append(
				ScheduledTask(
					task=task,
					start_time=start_dt,
					end_time=end_dt,
					reason=reason,
					pet_names=list(candidate.pet_names),
				)
			)

		scheduled.sort(key=lambda item: item.start_time)
		return scheduled, unscheduled

	def fill_remaining_slots(
		self,
		candidates: List[TaskCandidate],
		occupied: List[ScheduledTask],
		plan_date: date,
		day_start: datetime,
		day_end: datetime,
		available_minutes: int,
	) -> Tuple[List[ScheduledTask], List[TaskCandidate]]:
		"""Place flexible tasks into open time slots within remaining minutes."""
		scheduled: List[ScheduledTask] = []
		unscheduled: List[TaskCandidate] = []
		minutes_left = available_minutes

		for candidate in candidates:
			task = candidate.task
			if minutes_left <= 0:
				unscheduled.append(candidate)
				continue

			if task.duration_minutes > minutes_left:
				unscheduled.append(candidate)
				continue

			combined = occupied + scheduled
			start_dt = self._find_slot_for_task(task, combined, plan_date, day_start, day_end)
			if start_dt is None:
				unscheduled.append(candidate)
				continue

			end_dt = start_dt + timedelta(minutes=task.duration_minutes)
			reason = self._reason_for_task(task=task, start_dt=start_dt, pet_names=candidate.pet_names)
			scheduled.append(
				ScheduledTask(
					task=task,
					start_time=start_dt,
					end_time=end_dt,
					reason=reason,
					pet_names=list(candidate.pet_names),
				)
			)
			minutes_left -= task.duration_minutes

		scheduled.sort(key=lambda item: item.start_time)
		return scheduled, unscheduled

	def _resolve_day_bounds(self, owner: Owner, plan_date: date) -> Tuple[datetime, datetime]:
		"""Resolve schedule start and end times from defaults and owner preferences."""
		start = self.start_of_day
		end = self.end_of_day

		owner_start = owner.preferences.get("start_of_day") if owner.preferences else None
		owner_end = owner.preferences.get("end_of_day") if owner.preferences else None

		if owner_start:
			parsed = self._parse_time(owner_start)
			if parsed is not None:
				start = parsed

		if owner_end:
			parsed = self._parse_time(owner_end)
			if parsed is not None:
				end = parsed

		start_dt = datetime.combine(plan_date, start)
		end_dt = datetime.combine(plan_date, end)
		if end_dt <= start_dt:
			end_dt = start_dt + timedelta(hours=1)
		return start_dt, end_dt

	def _parse_time(self, value: str) -> Optional[time]:
		"""Parse a HH:MM string into a time object when valid."""
		try:
			parsed = datetime.strptime(value, "%H:%M")
			return parsed.time()
		except ValueError:
			return None

	def _has_overlap(self, start_dt: datetime, end_dt: datetime, scheduled: List[ScheduledTask]) -> bool:
		"""Check whether a candidate time range overlaps existing scheduled items."""
		for item in scheduled:
			if start_dt < item.end_time and end_dt > item.start_time:
				return True
		return False

	def _find_slot_for_task(
		self,
		task: Task,
		scheduled: List[ScheduledTask],
		plan_date: date,
		day_start: datetime,
		day_end: datetime,
	) -> Optional[datetime]:
		"""Find the earliest valid start time for a task within the day window."""
		if task.preferred_time is not None:
			preferred = datetime.combine(plan_date, task.preferred_time)
			preferred_end = preferred + timedelta(minutes=task.duration_minutes)
			if (
				preferred >= day_start
				and preferred_end <= day_end
				and not self._has_overlap(preferred, preferred_end, scheduled)
			):
				return preferred

		candidate = day_start
		while candidate + timedelta(minutes=task.duration_minutes) <= day_end:
			candidate_end = candidate + timedelta(minutes=task.duration_minutes)
			if not self._has_overlap(candidate, candidate_end, scheduled):
				return candidate

			next_time = None
			for item in sorted(scheduled, key=lambda value: value.start_time):
				if item.end_time > candidate:
					next_time = item.end_time
					break

			if next_time is None:
				break
			candidate = next_time

		return None

	def _reason_for_task(self, task: Task, start_dt: datetime, pet_names: Optional[List[str]] = None) -> str:
		"""Create a short explanation string for why a task was scheduled."""
		reason_parts = [f"Priority {task.priority}"]
		if task.is_fixed_time and task.preferred_time is not None:
			reason_parts.append(f"Fixed at {task.preferred_time.strftime('%H:%M')}")
		if task.preferred_time is not None and not task.is_fixed_time:
			reason_parts.append(f"Preferred around {task.preferred_time.strftime('%H:%M')}")
		if pet_names:
			reason_parts.append(f"Pets: {', '.join(pet_names)}")
		reason_parts.append(f"Scheduled at {start_dt.strftime('%H:%M')}")
		return "; ".join(reason_parts)


@dataclass
class PawPalSystem:
	owners: List[Owner] = field(default_factory=list)
	scheduler: Scheduler = field(default_factory=Scheduler)

	def add_owner(self, owner: Owner) -> None:
		"""Register a new owner in the system."""
		self.owners.append(owner)

	def add_pet(self, owner_id: str, pet: Pet) -> None:
		"""Add a pet to an existing owner by owner ID."""
		owner = self._find_owner(owner_id)
		if owner is None:
			raise ValueError(f"Owner not found: {owner_id}")
		owner.add_pet(pet)

	def add_task(self, pet_id: str, task: Task) -> None:
		"""Add a task to a pet by pet ID."""
		pet = self._find_pet(pet_id)
		if pet is None:
			raise ValueError(f"Pet not found: {pet_id}")
		pet.add_task(task)

	def complete_task(self, task_id: str, completed_on: Optional[date] = None) -> Optional[Task]:
		"""Mark a task completed and auto-create the next recurrence when needed."""
		pet, task = self._find_pet_and_task(task_id)
		if pet is None or task is None:
			raise ValueError(f"Task not found: {task_id}")

		if task.status == TaskStatus.COMPLETED:
			return None

		completion_date = completed_on or date.today()
		task.mark_completed()

		next_due = task.next_due_date(completion_date)
		if next_due is None:
			return None

		for existing_task in pet.tasks:
			if (
				existing_task.status == TaskStatus.PENDING
				and existing_task.title == task.title
				and existing_task.task_type == task.task_type
				and existing_task.due_date == next_due
			):
				return existing_task

		next_task = Task(
			title=task.title,
			task_type=task.task_type,
			duration_minutes=task.duration_minutes,
			priority=task.priority,
			due_date=next_due,
			preferred_time=task.preferred_time,
			is_fixed_time=task.is_fixed_time,
			recurrence=task.recurrence,
		)
		pet.add_task(next_task)
		return next_task

	def generate_daily_plan(self, owner_id: str, pet_id: str, plan_date: date) -> DailyPlan:
		"""Generate a daily plan for a pet owned by the given owner."""
		owner = self._find_owner(owner_id)
		if owner is None:
			raise ValueError(f"Owner not found: {owner_id}")

		pet = self._find_pet_for_owner(owner, pet_id)
		if pet is None:
			raise ValueError(f"Pet not found for owner {owner_id}: {pet_id}")

		return self.scheduler.create_daily_plan(owner=owner, pet=pet, plan_date=plan_date)

	def generate_owner_daily_plan(self, owner_id: str, plan_date: date) -> DailyPlan:
		"""Generate one daily plan across all pets for the given owner."""
		owner = self._find_owner(owner_id)
		if owner is None:
			raise ValueError(f"Owner not found: {owner_id}")

		return self.scheduler.create_owner_daily_plan(owner=owner, plan_date=plan_date)

	def _find_owner(self, owner_id: str) -> Optional[Owner]:
		"""Look up an owner by ID."""
		for owner in self.owners:
			if owner.owner_id == owner_id:
				return owner
		return None

	def _find_pet(self, pet_id: str) -> Optional[Pet]:
		"""Look up a pet by ID across all owners."""
		for owner in self.owners:
			for pet in owner.pets:
				if pet.pet_id == pet_id:
					return pet
		return None

	def _find_pet_for_owner(self, owner: Owner, pet_id: str) -> Optional[Pet]:
		"""Look up a pet by ID within a specific owner."""
		for pet in owner.pets:
			if pet.pet_id == pet_id:
				return pet
		return None

	def _find_pet_and_task(self, task_id: str) -> Tuple[Optional[Pet], Optional[Task]]:
		"""Find and return the pet/task pair for a task ID."""
		for owner in self.owners:
			for pet in owner.pets:
				for task in pet.tasks:
					if task.task_id == task_id:
						return pet, task
		return None, None
