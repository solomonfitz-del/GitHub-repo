# SiteForge Code Workflow

## Branch Strategy
- `main` — Production-ready code. Only merged via reviewed PRs.
- `feature/*` — All work happens on feature branches (e.g., `feature/scraper-module`).
- `fix/*` — Bug fixes (e.g., `fix/team-db-lock`).

## Workflow
1. Members create feature branches from `main`
2. Code is developed and tested on the feature branch
3. Members push and create a PR to `main`
4. PRs are reviewed by the team lead
5. Approved PRs are merged (squash merge preferred)
6. Feature branches are deleted after merge

## Code Standards
- Python: PEP 8, type hints where practical
- HTML/CSS: Clean, responsive, accessible
- Environment variables for all API keys and secrets
- `.env.example` files for documentation (never commit real keys)
- `requirements.txt` for Python dependencies

## PR Review Process
- The lead reviews all submitted code tasks
- If a task result includes a PR URL, the lead checks the PR before approving
- PRs must pass basic review: no secrets committed, no broken imports, reasonable structure