from pathlib import Path
import sys
from datetime import date, datetime, time, timedelta
import pytest

# Ensure project root is importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pawpal_system import Owner, PawPalSystem, Pet, ScheduledTask, Task, TaskRecurrence, TaskStatus, TaskType


def test_task_completion_changes_status_to_completed() -> None:
	task = Task(
		title="Give medication",
		task_type=TaskType.MEDICATION,
		duration_minutes=10,
		priority=5,
	)

	assert task.status == TaskStatus.PENDING
	task.mark_completed()
	assert task.status == TaskStatus.COMPLETED


def test_adding_task_to_pet_increases_task_count() -> None:
	pet = Pet(pet_id="pet-1", name="Mochi", species="dog", age=4)
	task = Task(
		title="Morning walk",
		task_type=TaskType.WALK,
		duration_minutes=30,
		priority=4,
	)

	assert len(pet.tasks) == 0
	pet.add_task(task)
	assert len(pet.tasks) == 1


def test_generate_owner_daily_plan_combines_pets_into_one_schedule() -> None:
	system = PawPalSystem()
	owner = Owner(owner_id="owner-1", name="Jordan", daily_available_minutes=180)
	system.add_owner(owner)

	mochi = Pet(pet_id="pet-1", name="Mochi", species="dog", age=4)
	luna = Pet(pet_id="pet-2", name="Luna", species="dog", age=2)
	system.add_pet("owner-1", mochi)
	system.add_pet("owner-1", luna)

	today = date.today()
	system.add_task(
		"pet-1",
		Task(
			title="Morning Walk",
			task_type=TaskType.WALK,
			duration_minutes=30,
			priority=5,
			due_date=today,
			preferred_time=time(8, 0),
			is_fixed_time=True,
		),
	)
	system.add_task(
		"pet-2",
		Task(
			title="Morning Walk",
			task_type=TaskType.WALK,
			duration_minutes=20,
			priority=4,
			due_date=today,
			preferred_time=time(8, 0),
			is_fixed_time=True,
		),
	)
	system.add_task(
		"pet-1",
		Task(
			title="Breakfast",
			task_type=TaskType.FEEDING,
			duration_minutes=15,
			priority=3,
			due_date=today,
			preferred_time=time(9, 0),
			is_fixed_time=False,
		),
	)

	plan = system.generate_owner_daily_plan("owner-1", today)

	walk_items = [item for item in plan.items if item.task.task_type == TaskType.WALK]
	assert len(walk_items) == 1
	assert set(walk_items[0].pet_names) == {"Mochi", "Luna"}
	assert walk_items[0].task.duration_minutes == 30
	assert any(item.task.title == "Breakfast" for item in plan.items)


def test_complete_daily_task_creates_next_day_task() -> None:
	system = PawPalSystem()
	owner = Owner(owner_id="owner-1", name="Jordan", daily_available_minutes=120)
	system.add_owner(owner)
	pet = Pet(pet_id="pet-1", name="Mochi", species="dog", age=4)
	system.add_pet("owner-1", pet)

	today = date.today()
	task = Task(
		title="Daily Medication",
		task_type=TaskType.MEDICATION,
		duration_minutes=10,
		priority=5,
		due_date=today,
		recurrence=TaskRecurrence.DAILY,
	)
	system.add_task("pet-1", task)

	next_task = system.complete_task(task.task_id, completed_on=today)

	assert next_task is not None
	assert task.status == TaskStatus.COMPLETED
	assert next_task.status == TaskStatus.PENDING
	assert next_task.due_date == today + timedelta(days=1)
	assert next_task.recurrence == TaskRecurrence.DAILY


def test_complete_weekly_task_creates_next_week_task() -> None:
	system = PawPalSystem()
	owner = Owner(owner_id="owner-1", name="Jordan", daily_available_minutes=120)
	system.add_owner(owner)
	pet = Pet(pet_id="pet-1", name="Mochi", species="dog", age=4)
	system.add_pet("owner-1", pet)

	today = date.today()
	task = Task(
		title="Weekly Grooming",
		task_type=TaskType.GROOMING,
		duration_minutes=30,
		priority=3,
		due_date=today,
		recurrence=TaskRecurrence.WEEKLY,
	)
	system.add_task("pet-1", task)

	next_task = system.complete_task(task.task_id, completed_on=today)

	assert next_task is not None
	assert task.status == TaskStatus.COMPLETED
	assert next_task.status == TaskStatus.PENDING
	assert next_task.due_date == today + timedelta(days=7)
	assert next_task.recurrence == TaskRecurrence.WEEKLY


def test_detect_time_conflicts_ignores_walk_to_walk_overlap() -> None:
	system = PawPalSystem()
	owner = Owner(owner_id="owner-1", name="Jordan", daily_available_minutes=180)
	system.add_owner(owner)

	mochi = Pet(pet_id="pet-1", name="Mochi", species="dog", age=4)
	luna = Pet(pet_id="pet-2", name="Luna", species="dog", age=2)
	system.add_pet("owner-1", mochi)
	system.add_pet("owner-1", luna)

	first_walk = Task(
		title="Walk Mochi",
		task_type=TaskType.WALK,
		duration_minutes=30,
		priority=5,
	)
	second_walk = Task(
		title="Walk Luna",
		task_type=TaskType.WALK,
		duration_minutes=30,
		priority=4,
	)
	feeding = Task(
		title="Breakfast",
		task_type=TaskType.FEEDING,
		duration_minutes=15,
		priority=4,
	)

	start = datetime.combine(date.today(), time(8, 0))
	walk_end = start + timedelta(minutes=30)
	feed_end = start + timedelta(minutes=15)

	conflicts = system.scheduler.detect_time_conflicts(
		[
			# Walk-to-walk overlap should be ignored.
			ScheduledTask(first_walk, start, walk_end, pet_names=["Mochi"]),
			ScheduledTask(second_walk, start, walk_end, pet_names=["Luna"]),
			# Walk-to-feeding overlap should be flagged.
			ScheduledTask(feeding, start, feed_end, pet_names=["Mochi"]),
		]
	)

	assert len(conflicts) == 2
	assert all("Breakfast" in conflict for conflict in conflicts)


if __name__ == "__main__":
	raise SystemExit(pytest.main([__file__, "-v"]))
