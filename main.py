from datetime import date, time

from pawpal_system import Owner, PawPalSystem, Pet, Task, TaskType


def build_demo_system() -> PawPalSystem:
	system = PawPalSystem()

	owner = Owner(
		owner_id="owner-1",
		name="Jordan",
		daily_available_minutes=180,
		preferences={"start_of_day": "07:00", "end_of_day": "21:00"},
	)
	system.add_owner(owner)

	mochi = Pet(pet_id="pet-1", name="Mochi", species="dog", age=4)
	luna = Pet(pet_id="pet-2", name="Luna", species="cat", age=2)

	system.add_pet(owner_id="owner-1", pet=mochi)
	system.add_pet(owner_id="owner-1", pet=luna)

	today = date.today()

	# Mochi tasks
	system.add_task(
		pet_id="pet-1",
		task=Task(
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
		pet_id="pet-1",
		task=Task(
			title="Breakfast",
			task_type=TaskType.FEEDING,
			duration_minutes=15,
			priority=4,
			due_date=today,
			preferred_time=time(8, 45),
			is_fixed_time=False,
		),
	)
	system.add_task(
		pet_id="pet-1",
		task=Task(
			title="Evening Walk",
			task_type=TaskType.WALK,
			duration_minutes=25,
			priority=4,
			due_date=today,
			preferred_time=time(18, 0),
			is_fixed_time=True,
		),
	)

	# Luna tasks
	system.add_task(
		pet_id="pet-2",
		task=Task(
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
		pet_id="pet-2",
		task=Task(
			title="Medication",
			task_type=TaskType.MEDICATION,
			duration_minutes=10,
			priority=5,
			due_date=today,
			preferred_time=time(9, 15),
			is_fixed_time=True,
		),
	)
	system.add_task(
		pet_id="pet-2",
		task=Task(
			title="Vet Appointment",
			task_type=TaskType.APPOINTMENT,
			duration_minutes=45,
			priority=5,
			due_date=today,
			preferred_time=time(14, 0),
			is_fixed_time=True,
		),
	)
	system.add_task(
		pet_id="pet-2",
		task=Task(
			title="Evening Playtime",
			task_type=TaskType.ENRICHMENT,
			duration_minutes=20,
			priority=3,
			due_date=today,
			preferred_time=time(19, 0),
			is_fixed_time=False,
		),
	)

	return system


def print_owner_plan(system: PawPalSystem, owner_id: str, owner_name: str) -> None:
	today = date.today()
	plan = system.generate_owner_daily_plan(owner_id=owner_id, plan_date=today)

	print(f"\n{owner_name}'s Combined Plan")
	if not plan.items:
		print("  No tasks scheduled.")
	else:
		for item in plan.items:
			task = item.task
			pets = ", ".join(item.pet_names) if item.pet_names else "Unknown pet"
			print(
				f"  {item.start_time.strftime('%H:%M')} - {item.end_time.strftime('%H:%M')} | "
				f"{task.title} ({task.task_type.value}) | Pets: {pets}"
			)

	if plan.unscheduled_tasks:
		print("  Unscheduled tasks:")
		for task in plan.unscheduled_tasks:
			print(f"    - {task.title}")


if __name__ == "__main__":
	pawpal = build_demo_system()

	print("Todays Schedule")
	print("===============")
	print_owner_plan(pawpal, owner_id="owner-1", owner_name="Jordan")
