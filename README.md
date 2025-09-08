# Umpire Assignment Platform

A Django-based platform for managing umpire assignments, schedules, and payments for baseball/softball leagues.

## Features

- **Data Management**: Track umpires, coaches, teams, towns, and league admins
- **Game Scheduling**: Manage games with date, time, and field assignments
- **Umpire Assignments**: Assign up to 2 umpires per game (plate/base or solo)
- **Payment Tracking**: Automatic payment calculation based on umpire status and position
- **CSV Import**: Bulk import data via CSV files for all entities
- **Weekly Schedule View**: View games and assignments by week
- **Payment Summary**: Track umpire earnings and payment status
- **Admin Interface**: Full Django admin for data management

## Local Development

### Quick Start

1. Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Create superuser (already created if using Docker):
```bash
python manage.py createsuperuser
# Or use default: username=admin, password=admin123
```

4. Run development server:
```bash
python manage.py runserver
```

5. Access the application:
- Main site: http://localhost:8000/
- Admin interface: http://localhost:8000/admin/
- Weekly schedule: http://localhost:8000/schedule/
- Payment tracking: http://localhost:8000/payments/

## Docker Deployment

### Using Docker Compose (Recommended for local development)

```bash
docker-compose up --build
```

### Using Podman Desktop

```bash
podman build -t umpire-assigner .
podman run -p 8000:8000 -v $(pwd)/db.sqlite3:/app/db.sqlite3 umpire-assigner
```

### Deploy to Render.com

1. Push your code to GitHub
2. Connect your GitHub repository to Render
3. Create a new Web Service
4. Use these settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn umpire_assigner.wsgi:application`
   - Add environment variable: `PYTHON_VERSION` = `3.12`

## Data Import

Sample CSV files are provided in the `sample_data/` directory. To import:

1. Log into the admin interface
2. Navigate to any model (Umpires, Teams, etc.)
3. Click "Import CSV" button
4. Upload the corresponding CSV file

### CSV Format Requirements

**Umpires** (`umpires.csv`):
- first_name, last_name, email, phone, adult (yes/no), patched (yes/no)

**Coaches** (`coaches.csv`):
- first_name, last_name, email, phone

**League Admins** (`league_admins.csv`):
- first_name, last_name, email, phone

**Towns** (`towns.csv`):
- name, league_admin_email (optional)

**Teams** (`teams.csv`):
- town, level (AAA/Minors/Majors), name (optional), coach_email (optional)

**Games** (`games.csv`):
- home_town, home_level, away_town, away_level, date (YYYY-MM-DD), time (8:00/10:15/12:30/2:45), field (A/B/C/D/E)

## Pay Rates Configuration

Default pay rates are:
- Solo Patched Umpire: $50
- Solo Unpatched Umpire: $40
- Plate Patched Umpire: $35
- Plate Unpatched Umpire: $30
- Base Umpire (always unpatched): $25

To modify pay rates:
1. Go to Admin → Pay Rates
2. Add a new pay rate configuration with the desired amounts
3. The most recent pay rate (by effective date) will be used

## Usage

### Assigning Umpires
1. Go to Admin → Games
2. Select a game
3. In the "Umpire assignments" section, add umpires and their positions
4. Pay amounts are calculated automatically based on current pay rates

### Viewing Weekly Schedule
- Navigate to http://localhost:8000/schedule/
- Use navigation buttons to view different weeks
- Shows all games with assigned umpires

### Tracking Payments
- Navigate to http://localhost:8000/payments/
- View total earned, paid, and balance due for each umpire
- Mark payments as paid through the admin interface

## Default Admin Credentials
- Username: `admin`
- Password: `admin123`

**Important**: Change these credentials in production!

## Environment Variables (Production)

- `SECRET_KEY`: Django secret key (generate a new one for production)
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Set to your domain name

## License

This project is provided as-is for managing umpire assignments.