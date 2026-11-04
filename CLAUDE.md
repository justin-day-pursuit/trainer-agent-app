# CLAUDE.md — Project Guidelines for Claude Code & CLI

## 📖 Mandatory Reading
All agent architecture principles, system prompts, harness standards, safety boundaries, and evaluation metrics are defined in [`agents.md`](./agents.md).
Read `agents.md` before writing or modifying any agent, prompt, or harness code.

## ⚡ Quick Operational Rules
1. **Secrets & Security**: Never commit `.env` files, actual credentials, or API tokens. Keep all secrets in `.env` (use `.env.example` as reference).
2. **Branch Discipline**: The project integration branch is `main`. Submit pull requests rather than pushing directly to `main`.
3. **Collaboration & Lane Ownership**: Check [`team-reference.md`](./team-reference.md) for active sprint tasks, completed items, and open architectural decisions before modifying shared modules.
4. **Code Quality**:
   - Write clear explanatory comments for functions and key blocks so non-technical stakeholders and future maintainers can easily understand them.
   - Run verification checks (`pytest tests/` for backend, `npm run build` for frontend) before finalizing changes.
