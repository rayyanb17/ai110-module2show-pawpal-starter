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

This is reasonable for this scenario because pet owners need a plan that is fast, predictable, and easy to understand. A fully optimized search might find slightly better minute-by-minute arrangements, but it would be more complex, harder to explain in the UI, and less maintainable. The current tradeoff gives strong practical behavior (including walk merging and conflict reporting) while keeping the app responsive and the scheduling decisions transparent.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
