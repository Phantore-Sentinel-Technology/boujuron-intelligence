# Boujuron Deployment Guide

## 1. Database: Neon PostgreSQL

1. Create a Neon project.
2. Copy the pooled PostgreSQL connection string.
3. Use it as `DATABASE_URL` on Render.
4. Keep SSL mode in the Neon URL if Neon includes it.

The API creates the required app tables automatically on first use.

## 2. Backend API: Render

Create a Render Web Service from this repository.

Recommended settings:

- Runtime: Docker
- Dockerfile: `Dockerfile`
- Start command:

```bash
uvicorn services.dashboard_service.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```text
ENVIRONMENT=production
DATABASE_URL=<your Neon pooled PostgreSQL URL>
JWT_SECRET=<long random secret>
FRONTEND_URL=https://<your-vercel-app>.vercel.app
CORS_ORIGINS=https://<your-vercel-app>.vercel.app
KAFKA_BOOTSTRAP_SERVER=
RISK_ENGINE_API=
```

After deploy, copy the Render service URL. Example:

```text
https://boujuron-api.onrender.com
```

## 3. Frontend: Vercel

Create a Vercel project using the `frontend` folder as the project root.

Recommended settings:

- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`

Environment variables:

```text
VITE_API_URL=https://<your-render-api>.onrender.com
VITE_WS_URL=wss://<your-render-api>.onrender.com/ws/fraud
```

The `frontend/vercel.json` file handles React Router refreshes.

## 4. Frontend: Netlify Alternative

Use the `frontend` folder as the base directory.

Settings:

- Build command: `npm run build`
- Publish directory: `frontend/dist`

Environment variables are the same as Vercel.

The `frontend/public/_redirects` file handles React Router refreshes.

## 5. Password Reset

The app now supports:

- `/forgot-password`
- `/reset-password?token=...`

In development, the API returns the reset link directly so you can test quickly.
In production, the API hides the token. Add an email provider later and send the generated reset URL from `/auth/forgot-password`.
