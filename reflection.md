# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML design used five core classes: Owner, Pet, Task, Scheduler, and DailyPlan. Each owner can own multiple pets, which each can have multiple tasks, which the Scheduler uses to produce a DailyPlan.

I assigned responsibilities as follows:

- Owner: stores owner profile info and preferences (for example available time windows and care priorities).
- Pet: stores pet details and acts as the container for that pet's care tasks.
- Task: represents one care action with fields for type (walk, feeding, medication, enrichment, grooming, appointment), duration, priority, and optional preferred/fixed time.
- Scheduler: applies the planning logic by placing fixed-time tasks first, then ordering the rest by priority and fit within available time.
- DailyPlan: stores the final scheduled tasks (and any unscheduled tasks) for a specific date so the UI can present a clear daily routine.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler considers these main constraints:

- Owner time budget (`daily_available_minutes`), so planned tasks do not exceed what the owner can realistically do.
- Day window preferences (`start_of_day`, `end_of_day`), so tasks are only scheduled in allowed hours.
- Fixed-time tasks and preferred times, where fixed tasks must happen at their exact time and preferred times are used when possible.
- Task urgency signals: due date first, then priority level, then duration as a tie-breaker.
- Multi-pet coordination, including combining compatible walk tasks so one walk can satisfy multiple pets.
- Conflict awareness: overlapping tasks are detected and reported (except walk-walk overlap, which is intentionally allowed).

I prioritized constraints in this order: safety/real-world feasibility first (time window and fixed-time rules), then urgency (due date + priority), then optimization (fit and combining walks). I chose this order because in a pet-care scenario, missing medication time or scheduling outside owner availability is more harmful than small efficiency losses. Once those hard constraints are respected, the scheduler can optimize convenience.

**b. Tradeoffs**

One tradeoff is that the scheduler favors deterministic, rule-based ordering over a globally optimal schedule. It places fixed-time tasks first, then schedules the remaining tasks by due date, priority, and fit, instead of running a heavier optimization algorithm across all combinations.

This is because of several reasons. First, it makes it far easier to explain the reasoning to a concerned pet owner. Seceondly, this ensures consitency with similar tasks and schedules, allowing pet owners to gain a general feel for how the day will plan out. Third, this approach is easier to test and maintain: each rule (fixed-time placement, prioritization, conflict detection, walk merging) can be validated independently, making bugs easier to find and fix. Finally, the app stays responsive in an interactive Streamlit workflow, where users expect near-instant plan updates after each input change. Overall, the design prioritizes consistency, transparency, and maintainability over marginal optimization.

---

## 3. AI Collaboration

**a. How you used AI**

I used AI throughout the project in three main ways: design brainstorming, targeted debugging, and test expansion. Early on, I used it to pressure-test my class structure and clarify responsibilities between `Owner`, `Pet`, `Task`, and `Scheduler` before writing full logic. During implementation, I used it to reason through scheduling edge cases (fixed-time behavior, overlap detection, and owner time-budget constraints) and to spot places where my assumptions did not match actual code behavior. I also used AI to propose additional tests so my verification covered not only common flows but also boundary conditions.

The most helpful prompts were specific, behavior-focused questions tied to the current codebase, such as: "What edge cases are missing from these scheduler tests?" and "Given this implementation, what should happen when available minutes are zero or negative?" Prompts that included exact constraints, expected outcomes, and the relevant file context produced much better results than broad prompts like "improve my scheduler." In practice, the best AI collaboration came from short iterative cycles: ask a focused question, apply a small change, run tests, and then refine.

**b. Judgment and verification**

One clear moment was when I explored the edge case where there was a fixed-time task with no preferred time. Initially, the AI wanted to make it so that fixed-time tasks with no preferred time was unscheduled, however, I decided it was better for it to just be treated as a regular task with flexible time.

I verified the suggestions by going over the code and running the test suite after each change. I compared expected behavior against the actual rule path in the code, then updated the test to reflect the current behavior and documented that behavior explicitly.

---

## 4. Testing and Verification

**a. What you tested**

I tested core scheduling and planning behavior, including task completion, recurring task creation (daily and weekly), multi-pet daily plan generation, walk merging, conflict detection rules, handling of zero and negative available minutes, fixed-time task boundaries, boundary-touching time slots, and behavior when no tasks exist.

These tests were important because they verify both normal workflows and failure paths, which gave me confidence that the planner is reliable in realistic day-to-day use.

**b. Confidence**

I am fairly confident the scheduler works correctly for the main project scenarios because the core planning rules and key edge cases are covered by tests and validated through repeated runs.

If I had more time, I would test duplicate tasks, more complex multi-pet schedules, and larger stress tests inputs with many tasks in one day.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
