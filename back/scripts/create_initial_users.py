import os
import django
import sys
from django.db import IntegrityError
from pathlib import Path

# Determine the base directory (assuming the script is in back/scripts)
# Adjust if the script location is different
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / 'apps'

# Add the apps directory to sys.path if it's not already there
# This helps Django find your apps
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# --- Add BASE_DIR to sys.path --- 
# This ensures Python can find the 'tcms' package containing settings.py
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
# --- End Add BASE_DIR ---

# Set up Django environment
# Assumes settings are in 'tcms.settings' relative to BASE_DIR ('back')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tcms.settings')
try:
    django.setup()
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc


from django.contrib.auth import get_user_model
User = get_user_model()

# --- IMPORTANT: Replace placeholder passwords before running! ---
USER_DATA = [
    {
        'username': 'admin_user',
        'email': 'admin@example.com',
        'password': '20021231', # Replace this!
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
        'name': 'Admin User', # Added name field
    },
    {
        'username': 'pm_user',
        'email': 'pm@example.com',
        'password': '20021231', # Replace this!
        'role': 'project_manager',
        'is_staff': False, # Adjust if needed
        'is_superuser': False,
        'name': 'Project Manager',
    },
    {
        'username': 'tester_user',
        'email': 'tester@example.com',
        'password': '20021231', # Replace this!
        'role': 'tester',
        'is_staff': False,
        'is_superuser': False,
        'name': 'Tester User',
    },
    {
        'username': 'dev_user',
        'email': 'dev@example.com',
        'password': '20021231', # Replace this!
        'role': 'developer',
        'is_staff': False,
        'is_superuser': False,
        'name': 'Developer User',
    },
]

print("Attempting to create initial users...")

users_created = 0
for data in USER_DATA:
    username = data['username']
    email = data['email']
    password = data['password']
    role = data['role']
    is_staff = data.get('is_staff', False)
    is_superuser = data.get('is_superuser', False)
    name = data.get('name', username) # Use username if name is not provided

    # Check if password is a placeholder
    if 'REPLACE_WITH' in password:
        print(f"Skipping user '{username}': Please replace the placeholder password in the script.")
        continue

    try:
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"User '{username}' already exists. Skipping.")
            continue
        if User.objects.filter(email=email).exists():
             print(f"User with email '{email}' already exists (maybe different username). Skipping '{username}'.")
             continue

        # Create user
        # Make sure your custom User model's create_user accepts 'role' and 'name'
        # If not, you might need to create the user first and then set the role/name and save.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,       # Pass role directly if create_user supports it
            name=name,       # Pass name directly if create_user supports it
            is_staff=is_staff,
            is_superuser=is_superuser
        )
        # If create_user doesn't handle role/name:
        # user = User.objects.create_user(username=username, email=email, password=password, is_staff=is_staff, is_superuser=is_superuser)
        # user.role = role
        # user.name = name
        # user.save()

        print(f"Successfully created user: {username} ({role})")
        users_created += 1
    except IntegrityError as e:
        print(f"Error creating user '{username}': {e}. Skipping.")
    except TypeError as e:
         print(f"TypeError creating user '{username}': {e}. Does your create_user method accept 'role' and 'name' arguments? Skipping.")
    except Exception as e:
        print(f"An unexpected error occurred for user '{username}': {e}. Skipping.")

print(f"User creation process finished. {users_created} users created.") 