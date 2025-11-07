#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# --- ОСЬ ОНОВЛЕННЯ ---
# Ми більше не довіряємо простому 'migrate'.
# Ми примусово запускаємо міграції для КОЖНОГО додатка.
echo "Running migrations for built-in apps..."
python manage.py migrate auth
python manage.py migrate contenttypes
python manage.py migrate sessions
python manage.py migrate admin

echo "Running migrations for OUR apps..."
# Ось "таран", який має пробити стіну.
python manage.py migrate store
python manage.py migrate users

echo "Build script finished."
