from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Owner, PawPalSystem, Pet, Task, TaskRecurrence, TaskStatus, TaskType


PRIORITY_MAP = {"Low": 1, "Medium": 3, "High": 5}
RECURRENCE_MAP = {"None": TaskRecurrence.NONE, "Daily": TaskRecurrence.DAILY, "Weekly": TaskRecurrence.WEEKLY}


def task_to_state(task: Task, pet_id: str) -> dict:
    """Convert a task to a session-state-friendly dictionary."""
    return {
        "task_id": task.task_id,
        "pet_id": pet_id,
        "title": task.title,
        "task_type": task.task_type.name,
        "duration_minutes": task.duration_minutes,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else date.today().isoformat(),
        "preferred_time": task.preferred_time.strftime("%H:%M") if task.preferred_time else None,
        "is_fixed_time": task.is_fixed_time,
        "status": task.status.name,
        "recurrence": task.recurrence.name,
    }


def sync_state_from_system(system: PawPalSystem) -> None:
    """Persist owners/pets/tasks from system object into session state."""
    st.session_state.owners = [
        {
            "owner_id": owner.owner_id,
            "name": owner.name,
            "daily_available_minutes": owner.daily_available_minutes,
            "preferences": owner.preferences,
        }
        for owner in system.owners
    ]

    st.session_state.pets = []
    st.session_state.tasks = []
    for owner in system.owners:
        for pet in owner.pets:
            st.session_state.pets.append(
                {
                    "pet_id": pet.pet_id,
                    "owner_id": owner.owner_id,
                    "name": pet.name,
                    "species": pet.species,
                    "age": pet.age,
                    "health_notes": pet.health_notes,
                }
            )
            for task in pet.tasks:
                st.session_state.tasks.append(task_to_state(task, pet.pet_id))


def initialize_state() -> None:
    """Initialize session collections used to persist owner, pet, and task data."""
    if "owners" not in st.session_state:
        st.session_state.owners = []
    if "pets" not in st.session_state:
        st.session_state.pets = []
    if "tasks" not in st.session_state:
        st.session_state.tasks = []


def get_system() -> PawPalSystem:
    """Rebuild a PawPalSystem from data persisted in session state."""
    system = PawPalSystem()

    for owner_data in st.session_state.owners:
        owner = Owner(
            owner_id=owner_data["owner_id"],
            name=owner_data["name"],
            daily_available_minutes=owner_data["daily_available_minutes"],
            preferences=owner_data["preferences"],
        )
        system.add_owner(owner)

    for pet_data in st.session_state.pets:
        pet = Pet(
            pet_id=pet_data["pet_id"],
            name=pet_data["name"],
            species=pet_data["species"],
            age=pet_data["age"],
            health_notes=pet_data["health_notes"],
        )
        system.add_pet(pet_data["owner_id"], pet)

    for task_data in st.session_state.tasks:
        preferred_time = None
        if task_data["preferred_time"]:
            preferred_time = datetime.strptime(task_data["preferred_time"], "%H:%M").time()

        task = Task(
            title=task_data["title"],
            task_type=TaskType[task_data["task_type"]],
            duration_minutes=task_data["duration_minutes"],
            priority=task_data["priority"],
            due_date=date.fromisoformat(task_data["due_date"]),
            preferred_time=preferred_time,
            is_fixed_time=task_data["is_fixed_time"],
            recurrence=TaskRecurrence[task_data.get("recurrence", "NONE")],
            status=TaskStatus[task_data.get("status", "PENDING")],
            task_id=task_data["task_id"],
        )
        system.add_task(task_data["pet_id"], task)

    return system


def next_owner_id(system: PawPalSystem) -> str:
    """Create the next owner ID based on current owner count."""
    return f"owner-{len(system.owners) + 1}"


def next_pet_id(system: PawPalSystem) -> str:
    """Create the next pet ID based on total pets across owners."""
    total_pets = sum(len(owner.pets) for owner in system.owners)
    return f"pet-{total_pets + 1}"


def owner_options(system: PawPalSystem) -> dict[str, str]:
    """Build owner select options as label -> owner_id mapping."""
    return {f"{owner.name} ({owner.owner_id})": owner.owner_id for owner in system.owners}


def pet_options(owner: Owner) -> dict[str, str]:
    """Build pet select options for one owner as label -> pet_id mapping."""
    return {f"{pet.name} ({pet.species})": pet.pet_id for pet in owner.pets}


def find_owner(system: PawPalSystem, owner_id: str) -> Owner | None:
    """Return owner matching owner_id, if present."""
    for owner in system.owners:
        if owner.owner_id == owner_id:
            return owner
    return None


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Plan pet care tasks with priorities, preferred times, and a generated daily schedule.")

initialize_state()
system = get_system()

st.subheader("1) Add Owner")
with st.form("owner_form", clear_on_submit=True):
    owner_name = st.text_input("Owner name", placeholder="Jordan")
    daily_minutes = st.number_input("Daily available minutes", min_value=30, max_value=1440, value=180, step=15)
    start_of_day = st.time_input("Start of day", value=time(7, 0))
    end_of_day = st.time_input("End of day", value=time(21, 0))
    add_owner_clicked = st.form_submit_button("Add owner")

if add_owner_clicked:
    if not owner_name.strip():
        st.error("Owner name is required.")
    else:
        owner = Owner(
            owner_id=next_owner_id(system),
            name=owner_name.strip(),
            daily_available_minutes=int(daily_minutes),
            preferences={
                "start_of_day": start_of_day.strftime("%H:%M"),
                "end_of_day": end_of_day.strftime("%H:%M"),
            },
        )
        st.session_state.owners.append(
            {
                "owner_id": owner.owner_id,
                "name": owner.name,
                "daily_available_minutes": owner.daily_available_minutes,
                "preferences": owner.preferences,
            }
        )
        system = get_system()
        st.success(f"Added owner: {owner.name}")

st.divider()
st.subheader("2) Add Pet")

if not system.owners:
    st.info("Add an owner first.")
else:
    owner_label_to_id = owner_options(system)
    owner_label = st.selectbox("Choose owner", list(owner_label_to_id.keys()), key="pet_owner_select")
    selected_owner_id = owner_label_to_id[owner_label]

    with st.form("pet_form", clear_on_submit=True):
        pet_name = st.text_input("Pet name", placeholder="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "other"])
        age = st.number_input("Age", min_value=0, max_value=50, value=2)
        health_notes = st.text_input("Health notes", placeholder="Allergy to chicken")
        add_pet_clicked = st.form_submit_button("Add pet")

    if add_pet_clicked:
        if not pet_name.strip():
            st.error("Pet name is required.")
        else:
            pet = Pet(
                pet_id=next_pet_id(system),
                name=pet_name.strip(),
                species=species,
                age=int(age),
                health_notes=health_notes.strip(),
            )
            st.session_state.pets.append(
                {
                    "pet_id": pet.pet_id,
                    "owner_id": selected_owner_id,
                    "name": pet.name,
                    "species": pet.species,
                    "age": pet.age,
                    "health_notes": pet.health_notes,
                }
            )
            system = get_system()
            st.success(f"Added pet: {pet.name}")

st.divider()
st.subheader("3) Add Task")

if not system.owners:
    st.info("Add an owner and pet before adding tasks.")
else:
    owner_label_to_id = owner_options(system)
    task_owner_label = st.selectbox("Owner", list(owner_label_to_id.keys()), key="task_owner_select")
    task_owner_id = owner_label_to_id[task_owner_label]
    task_owner = find_owner(system, task_owner_id)

    if task_owner is None or not task_owner.pets:
        st.info("Selected owner has no pets yet.")
    else:
        pet_label_to_id = pet_options(task_owner)
        task_pet_label = st.selectbox("Pet", list(pet_label_to_id.keys()), key="task_pet_select")
        task_pet_id = pet_label_to_id[task_pet_label]

        with st.form("task_form", clear_on_submit=True):
            task_title = st.text_input("Task title", placeholder="Morning walk")
            task_type_label = st.selectbox(
                "Task type",
                ["WALK", "FEEDING", "MEDICATION", "ENRICHMENT", "GROOMING", "APPOINTMENT"],
            )
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=360, value=20)
            priority_label = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
            recurrence_label = st.selectbox("Recurrence", ["None", "Daily", "Weekly"], index=0)
            due_date = st.date_input("Due date", value=date.today())
            preferred_time = st.time_input("Preferred time")
            is_fixed = st.checkbox("Fixed time (must occur exactly at preferred time)", value=False)
            add_task_clicked = st.form_submit_button("Add task")

        if add_task_clicked:
            if not task_title.strip():
                st.error("Task title is required.")
            else:
                task = Task(
                    title=task_title.strip(),
                    task_type=TaskType[task_type_label],
                    duration_minutes=int(duration),
                    priority=PRIORITY_MAP[priority_label],
                    due_date=due_date,
                    preferred_time=preferred_time,
                    is_fixed_time=is_fixed,
                    recurrence=RECURRENCE_MAP[recurrence_label],
                )
                st.session_state.tasks.append(task_to_state(task, task_pet_id))
                system = get_system()
                st.success(f"Added task: {task.title}")

st.divider()
st.subheader("Current Data")

if not system.owners:
    st.info("No owners yet.")
else:
    col1, col2 = st.columns(2)
    with col1:
        filter_status = st.multiselect(
            "Filter by status",
            ["Pending", "Completed", "Skipped"],
            default=["Pending", "Completed", "Skipped"],
            key="task_status_filter",
        )
    with col2:
        all_pets = []
        for owner in system.owners:
            for pet in owner.pets:
                all_pets.append(f"{pet.name} ({owner.name})")
        
        filter_pets = st.multiselect(
            "Filter by pet",
            all_pets,
            default=all_pets,
            key="task_pet_filter",
        )
    
    filtered_pet_names = {pet_label.split(" (")[0] for pet_label in filter_pets}
    status_map = {"Pending": "pending", "Completed": "completed", "Skipped": "skipped"}
    filtered_statuses = [status_map[s] for s in filter_status]
    
    for owner in system.owners:
        st.markdown(f"**Owner:** {owner.name} ({owner.owner_id})")
        st.caption(
            f"Available minutes: {owner.daily_available_minutes} | "
            f"Day: {owner.preferences.get('start_of_day', '06:00')} - {owner.preferences.get('end_of_day', '22:00')}"
        )
        if not owner.pets:
            st.write("No pets yet.")
            continue
        for pet in owner.pets:
            if pet.name not in filtered_pet_names:
                continue
            st.write(f"- {pet.name} ({pet.species}, age {pet.age})")
            filtered_tasks = [
                task for task in pet.tasks
                if task.status.value in filtered_statuses
            ]
            if filtered_tasks:
                st.table(
                    [
                        {
                            "Title": task.title,
                            "Type": task.task_type.value,
                            "Duration": task.duration_minutes,
                            "Priority": task.priority,
                            "Status": task.status.value,
                            "Recurrence": task.recurrence.value,
                            "Due": task.due_date,
                            "Preferred": task.preferred_time.strftime("%H:%M") if task.preferred_time else "-",
                            "Fixed": task.is_fixed_time,
                        }
                        for task in filtered_tasks
                    ]
                )
            else:
                st.write("  No tasks match filters.")

st.divider()
st.subheader("4) Complete Task")

pending_options: dict[str, str] = {}
for owner in system.owners:
    for pet in owner.pets:
        for task in pet.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            label = (
                f"{owner.name} | {pet.name} | {task.title} "
                f"(due {task.due_date.isoformat() if task.due_date else 'none'})"
            )
            pending_options[label] = task.task_id

if not pending_options:
    st.info("No pending tasks available to complete.")
else:
    complete_label = st.selectbox("Pending task", list(pending_options.keys()), key="complete_task_select")
    if st.button("Mark task completed"):
        completed_task_id = pending_options[complete_label]
        next_task = system.complete_task(completed_task_id, completed_on=date.today())
        sync_state_from_system(system)
        if next_task is None:
            st.success("Task marked completed.")
        else:
            recurrence_name = next_task.recurrence.value
            due_label = next_task.due_date.isoformat() if next_task.due_date else "none"
            st.success(f"Task completed. Added next {recurrence_name} task due on {due_label}.")

st.divider()
st.subheader("5) Generate Schedule")

if not system.owners:
    st.info("Add data first, then generate a schedule.")
else:
    schedule_owner_map = owner_options(system)
    schedule_owner_label = st.selectbox("Owner for schedule", list(schedule_owner_map.keys()), key="schedule_owner_select")
    schedule_owner_id = schedule_owner_map[schedule_owner_label]
    schedule_owner = find_owner(system, schedule_owner_id)

    if schedule_owner is None or not schedule_owner.pets:
        st.info("Selected owner has no pets yet.")
    else:
        plan_date = st.date_input("Plan date", value=date.today(), key="plan_date")

        if st.button("Generate combined schedule", type="primary"):
            try:
                plan = system.generate_owner_daily_plan(schedule_owner_id, plan_date)
                st.success("Schedule generated.")
                st.write(plan.get_summary())

                if plan.items:
                    st.table(
                        [
                            {
                                "Start": item.start_time.strftime("%H:%M"),
                                "End": item.end_time.strftime("%H:%M"),
                                "Task": item.task.title,
                                "Type": item.task.task_type.value,
                                "Pets": ", ".join(item.pet_names) if item.pet_names else "-",
                                "Reason": item.reason,
                            }
                            for item in plan.items
                        ]
                    )

                    if plan.conflicts:
                        st.error("Conflicting task times detected (walk-walk overlap is allowed).")
                        st.table([{"Conflict": conflict} for conflict in plan.conflicts])
                else:
                    st.info("No tasks were scheduled for this date.")

                if plan.unscheduled_tasks:
                    st.warning("Some tasks could not be scheduled.")
                    unscheduled_data = []
                    for task in plan.unscheduled_tasks:
                        pet = None
                        for owner in system.owners:
                            for p in owner.pets:
                                if any(t.task_id == task.task_id for t in p.tasks):
                                    pet = p
                                    break
                        pet_name = pet.name if pet else "Unknown"
                        unscheduled_data.append({
                            "Task": task.title,
                            "Pet": pet_name,
                            "Type": task.task_type.value,
                            "Duration": task.duration_minutes,
                            "Priority": task.priority,
                            "Status": task.status.value,
                        })
                    st.table(unscheduled_data)
            except ValueError as error:
                st.error(str(error))
