# Architecture and agent workflow diagrams

| File | What it shows |
|---|---|
| `architecture.png` / `.pdf` | Who uses the app, the Vercel frontend, the FastAPI backend on Render with the three AI agents and the Progression Engine, Supabase, and the Anthropic API. Dashed cards are AI: they read and draft only, with no database writes and no sending. |
| `agent-workflow.png` / `.pdf` | The weekly loop in four lanes (client, AI, code, trainer) and the check-in loop, with the three human checkpoints and the guardrails. |

Both are 1920×1080 so they drop straight into a 16:9 slide.

To edit, change the HTML in `source/` and re-render (needs Node and Playwright):

```bash
cd presentation/diagrams/source && node render.mjs architecture agent-workflow
```
