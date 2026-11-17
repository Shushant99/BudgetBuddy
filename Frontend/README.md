# BudgetBuddy frontend

The React and Vite application for BudgetBuddy. It includes account sign-in and
registration, a monthly overview, transaction history, budgets, savings goals,
contributions, and Premium upgrade requests.

## Run locally

```bash
npm install
npm run dev
```

By default, Vite proxies `/api` requests to Django at `http://127.0.0.1:8000`.
Set `VITE_API_BASE_URL` in a local `.env` file if the API is hosted elsewhere.
Do not include secrets in frontend environment variables; Vite exposes them to
the browser.

## Other commands

```bash
npm run lint
npm run build
npm run preview
```

The UI uses Django's token-authenticated `/api` endpoints. The backend must be
running and configured before sign-in or data operations will work.
