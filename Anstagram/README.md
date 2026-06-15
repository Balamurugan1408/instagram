# Anstagram

A full-stack Instagram-like social app scaffold with a Django REST Framework backend and a React/Vite frontend.

## Features

- JWT authentication with registration, login, refresh, and profile endpoints
- Posts with image upload, captions, hashtags, likes, comments, saves, and shares
- Follow/unfollow relationships
- Notifications for likes, comments, and follows
- Stories and reels/short videos
- Direct message conversations
- Search across users, posts, and hashtags
- Explore feed
- Responsive mobile-first React UI with dark mode

## Project Structure

```text
backend/
  anstagram/        Django project settings
  social/           API app: models, serializers, views, routes
  media/            Uploaded files in development
frontend/
  src/              React application
  public/           Static public assets
```

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`.

## Frontend Setup

Install Node.js first, then:

```powershell
cd frontend
npm install
npm run dev
```

The app runs at `http://127.0.0.1:5173/`.

## PostgreSQL

The backend defaults to SQLite for quick local development. To use PostgreSQL, set:

```env
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/anstagram
```

## Deployment Guide

1. Set `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, and CORS origins in production.
2. Use PostgreSQL, object storage for media, HTTPS, and a reverse proxy such as Nginx.
3. Run `python manage.py collectstatic`.
4. Serve Django with Gunicorn/Uvicorn workers.
5. Build the React app with `npm run build` and serve `frontend/dist`.
6. Add Redis/Celery or Django Channels for production-grade real-time delivery.

## API Documentation

After running the backend, browse:

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`
