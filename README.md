# Assistly

Assistly is a Flask and MongoDB community support platform for residents, volunteers, and administrators. It provides request management, community coordination, direct messaging, volunteer ratings, and analytics in a professional role-based workspace.

## What Assistly Does

- Resident and volunteer modes with role-aware navigation
- Community join and approval workflows
- Request creation, assignment, progress tracking, and completion
- Volunteer ratings and feedback after completion
- Direct messaging between users
- Analytics dashboards for platform, community, and user insights
- Email notifications and weekly digest support
- MongoDB bootstrap script for collections and indexes

## Phase 1 Included

The current codebase includes the first major feature phase:

- Request tags for better categorization and filtering
- Volunteer rating and review flow
- Completion confirmation workflow for residents
- Direct messaging inbox and conversation screens
- Analytics dashboard with request, volunteer, and activity metrics
- Email notification service for welcome, completion, and digest emails
- Bootstrap script that creates the required MongoDB collections and indexes

## Tech Stack

- Backend: Flask, Flask-Login, Flask-SocketIO, Authlib
- Database: MongoDB with PyMongo
- Frontend: Jinja2 templates, Bootstrap 5, custom CSS, JavaScript
- Runtime: Gunicorn for deployment

## Project Structure

```text
Assistly-python/
  app.py
  config.py
  bootstrap_collections.py
  requirements.txt
  routes/
  models/
  templates/
  static/
  analytics/
```

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`.

```env
SECRET_KEY=your-secret-key
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority
DB_NAME=assistly_db
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM=your-email@example.com
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback
ATLAS_CHART_STATUS_URL=https://charts.mongodb.com/charts-<app-id>/embed/charts?id=<status-chart-id>&maxDataAge=3600&theme=light&autoRefresh=true
ATLAS_CHART_CATEGORIES_URL=https://charts.mongodb.com/charts-<app-id>/embed/charts?id=<categories-chart-id>&maxDataAge=3600&theme=light&autoRefresh=true
ATLAS_CHART_ACTIVITY_URL=https://charts.mongodb.com/charts-<app-id>/embed/charts?id=<activity-chart-id>&maxDataAge=3600&theme=light&autoRefresh=true
```

4. Bootstrap collections and indexes.

```bash
.venv/bin/python bootstrap_collections.py
```

5. Start the application.

```bash
.venv/bin/python app.py
```

6. Open the app.

```text
http://127.0.0.1:5000
```

## Useful Routes

### Authentication

- `/signup`
- `/login`
- `/logout`

### Dashboard

- `/dashboard`
- `/dashboard/user`
- `/dashboard/admin`

### Requests

- `GET /requests/create`
- `POST /requests/create`
- `POST /requests/<id>/update`
- `POST /requests/<id>/status`
- `POST /requests/<id>/delete`
- `POST /requests/<id>/accept`
- `POST /requests/<id>/complete`

### Communities

- `/communities/`
- `POST /communities/<id>/join`
- `POST /communities/create`
- `POST /communities/<id>/delete`

### Phase 1 Features

- `/ratings/request/<request_id>/rate`
- `/ratings/request/<request_id>/confirm-complete`
- `/ratings/volunteer/<volunteer_id>`
- `/messaging/`
- `/messaging/conversation/<other_user_id>`
- `/messaging/send`
- `/analytics/dashboard`

## MongoDB Collections

The application now uses these collections:

- `users`
- `requests`
- `communities`
- `community_invites`
- `community_messages`
- `admin_access_requests`
- `email_verifications`
- `volunteer_profiles`
- `volunteer_ratings`
- `conversations`
- `messages`

## Deployment

### Best Free Deployment Option: Render

Render is the best free-first platform for this app because it supports Python web services, connects easily to GitHub, and works well with MongoDB Atlas.

#### Steps

1. Push the latest code to GitHub.
2. Create a free MongoDB Atlas cluster if you have not already.
3. In Render, create a new **Web Service** from your GitHub repository.
4. Use these settings:
  - **Environment:** Python
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn wsgi:app`
5. Add these environment variables in Render:
  - `SECRET_KEY`
  - `MONGO_URI`
  - `DB_NAME`
  - `SMTP_HOST`
  - `SMTP_PORT`
  - `SMTP_USER`
  - `SMTP_PASSWORD`
  - `SMTP_USE_TLS`
  - `EMAIL_FROM`
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REDIRECT_URI`
  - `ATLAS_CHART_STATUS_URL` (optional, enables Atlas embed in analytics dashboard)
  - `ATLAS_CHART_CATEGORIES_URL` (optional, enables Atlas embed in analytics dashboard)
  - `ATLAS_CHART_ACTIVITY_URL` (optional, enables Atlas embed in analytics dashboard)
6. Deploy the service.
7. After the first successful deploy, run `bootstrap_collections.py` once if needed to ensure collections and indexes exist.

### Local Development

- Use `.venv/bin/python app.py`

### Production Notes

- The app now uses `wsgi.py` as the production entrypoint.
- MongoDB Atlas is the recommended free database backend.
- Render's free tier may sleep when idle, so first-load latency can happen.

## Notes

- The bootstrap script is safe to run multiple times.
- The application will create MongoDB collections on first use if they do not already exist.
- The analytics and messaging pages require authentication.

## Next Steps

- Add more request filters and search
- Expand volunteer skill matching
- Add exportable analytics reports
- Add email scheduling/background jobs
