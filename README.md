# BudgetBuddy-Ai-Tool
Infosys Internship Project – BudgetBuddy: Full-Stack Personal Budget Planning and Expense Management Platform

## Backend setup

1. Install the backend dependencies:

   ```bash
   cd Backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` if `.env` does not already exist. Set a unique
   `DJANGO_SECRET_KEY` and your MySQL `DB_USER` and `DB_PASSWORD` in `.env`.
   Keep `.env` private; only commit `.env.example`.

3. Create the database in MySQL (using an account with database-creation
   privileges):

   ```bash
   mysql -u <admin-user> -p -e 'CREATE DATABASE `budgetbuddy-clone` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
   ```

   Configure the database host, port, name, and application credentials using
   the `DB_*` variables in `.env`.

4. Apply migrations and start Django:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
