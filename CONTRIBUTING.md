# Contributing to RiskSure

Thanks for your interest in improving RiskSure! This guide explains how to propose a change and get it merged.

## 1. Find or open an issue
* Browse the [open issues](https://github.com/Moukthika6706/InsureTech-risksure/issues).
* Comment on the one you'd like to work on, and **wait until you are assigned** before starting. This avoids two people building the same thing.
* For a new idea or bug, open an issue first and describe the problem, the expected behaviour, and how to reproduce it.

## 2. Set up the project
Follow the **Getting Started** section of the [README](./README.md): fork, clone, add the `upstream` remote, set up the backend and frontend, and check that `pytest -q` passes.

Keep your fork up to date before you start:
```bash
git fetch upstream
git checkout main
git merge upstream/main
```

## 3. Create a branch
Never commit directly to `main`. Use a short, descriptive branch name:
```bash
git checkout -b feat/override-limits      # new feature
git checkout -b fix/waterfall-mobile      # bug fix
git checkout -b docs/readme-typos         # documentation
```

## 4. Make your change
* **Keep it focused** on the assigned issue: no unrelated refactors or formatting changes.
* **Respect the design ideas:**
  * Rates, rating tables, rules and product details live in `config/*.yaml`, never hard-coded in Python.
  * The rules engine is plain, deterministic code. The AI assistant only *drafts* rules, and a person publishes them.
  * Every status change goes through `backend/app/lifecycle.py`, so it writes an audit event.
* **Add or update tests** for behaviour you change (`backend/tests/`).
* Match the style of the surrounding code: small functions, short comments, clear names.

## 5. Check before you push
```bash
# backend (from backend/, virtual environment active)
pytest -q

# frontend (from frontend/)
npm run lint
npm run build
```

## 6. Commit and open a pull request
* Write clear, present-tense commit messages, e.g. `Limit underwriter overrides to the product minimum premium`.
* Push your branch and open a pull request against `main`.
* In the description, explain **what** changed and **why**, add screenshots for UI changes, and link the issue (`Closes #42`).
* Be ready to respond to review comments. Small follow-up commits on the same branch are fine.

## Code of conduct
Be kind and constructive. Assume good intent, give specific feedback, and help newcomers.
