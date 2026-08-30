# Career Lifecycle & Do This Next

Job Finder now treats every tracked opportunity as a state machine with one recommended next action.

```text
saved -> ready -> applied -> interview -> offer -> negotiation -> accepted
             \-> rejected (from any active stage)
```

Outreach is an execution layer around the lifecycle, not a fake application status. When a submitted application has relevant contacts, **Do This Next** can prioritize outreach, follow-up, or a reply before moving the user into interview preparation.

## Rules

- **Do This Next** returns exactly one highest-priority action per opportunity.
- Internal transitions are validated by `src/lifecycle.py`.
- External actions (email, LinkedIn, application submission) are never silently claimed as completed.
- Application submission becomes `applied` only after proof is logged.
- `offer -> negotiation` is an internal transition started from the action queue.
- `negotiation -> accepted` requires explicit confirmation in the UI.
- Rejected is a terminal state and can be recorded from any active stage.

## API

- `GET /api/action-queue` — ranked next actions across the pipeline.
- `POST /api/opportunities/{job_id}/do-next` — executes the safest internal step or returns the external destination.
- `POST /api/applications/{application_id}/transition` — validated milestone transition.
- `GET /api/opportunities/{job_id}/brief` — single-opportunity command center.
- `POST /api/applications/{application_id}/proof` — records evidence of an external submission and moves the application to `applied`.

The frontend dashboard surfaces the queue directly, while the Opportunity Brief remains the detailed decision screen.
