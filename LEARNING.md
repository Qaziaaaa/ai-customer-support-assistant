# LEARNING.md — step-by-step notes

Each project step adds a section here: **what** changed, **why** it exists,
and **where** to look in the code.

---

## Step 1 — Project skeleton

**What:** git repo, folder structure, `.env.example`, NovaMart mock data.

**Why this layout:**
- `src/data/` holds *facts* (orders, policies) separate from *logic* — later
  you can swap the dict for a real database without touching the agent code.
- `streamlit_app.py` will be UI-only; `src/graph.py` will be workflow-only.
  Separating layers now is what makes future RAG / multi-agent additions
  drop-in instead of rewrites.
- `.env` is gitignored so keys never enter history; `.env.example` documents
  exactly which variables the app expects.

**Why mock data as a dict?** Tool calling needs something deterministic to
retrieve. A dict keeps the first lesson about tools focused on the *mechanism*
(JSON schema → LLM emits call → function runs → result returns), not on SQL.

**Try it:**
```bash
python3 -c "from src.data.orders import get_order; print(get_order('ord-1001'))"
```
