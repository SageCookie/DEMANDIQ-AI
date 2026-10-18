# Free deployment guide

This guide deploys the public dashboard on **Vercel**, the FastAPI service on
**Render**, and the PostgreSQL database on **Neon**. It is the best free setup
for a portfolio, college demonstration, or small internal trial.

## Before you start

1. Sign up for free accounts at [GitHub](https://github.com),
   [Neon](https://neon.com), [Render](https://render.com), and
   [Vercel](https://vercel.com). Use the same GitHub account to make the
   connections simpler.
2. Push the latest project files to the `main` branch of your GitHub
   repository. From the project folder, use the following commands (review the
   file list shown by `git status` before committing):

   ```powershell
   git add .gitignore README.md DEPLOYMENT.md render.yaml vercel.json src alembic dashboard/src/lib dashboard/src/vite-env.d.ts
   git commit -m "Prepare free cloud deployment"
   git push origin main
   ```

   Do **not** upload `.env`, `demandiq.db`, or database backups.
3. Confirm that these two tracked files exist in GitHub before deploying:
   `models/production/demand_model.joblib` and
   `data/raw/historical_sales.csv`. They provide the initial forecast model
   and demonstration data.

## 1. Create the free PostgreSQL database (Neon)

1. Open the Neon dashboard and select **Create project**.
2. Give it a name such as `demandiq-production`, select a region near you, and
   create the project.
3. On the project dashboard, click **Connect**.
4. Copy the complete connection string that starts with `postgresql://`.
   Leave all Neon defaults unchanged. Keep this value private; it is the
   database password as well as the address.

## 2. Deploy the backend API (Render)

1. In Render, select **New** → **Blueprint**.
2. Connect GitHub if prompted, select the `DEMANDIQ-AI` repository, then
   select the `main` branch.
3. Render detects `render.yaml`. Give the Blueprint permission to create the
   `demandiq-api` web service and select **Apply**.
4. When Render asks for environment values, enter the following:

   | Key | Exact value |
   | --- | --- |
   | `DATABASE_URL` | Paste the private Neon connection string from step 1. |
   | `CORS_ORIGINS` | `http://localhost:5173` for now. You will replace this after Vercel gives you the public dashboard URL. |
   | `INITIAL_ADMIN_USERNAME` | Your chosen sign-in name, for example `admin`. |
   | `INITIAL_ADMIN_PASSWORD` | A unique password of at least 12 characters. |

   `APP_ENV`, `PYTHON_VERSION`, and `SECRET_KEY` are already defined safely by
   `render.yaml`; do not change them.
5. Select **Create Blueprint**. Wait until the deploy log finishes with a
   successful start message.
6. Open `https://YOUR-RENDER-SERVICE.onrender.com/api/v1/health` in a browser.
   It must return a small JSON response with `"status": "healthy"`. Also open
   `https://YOUR-RENDER-SERVICE.onrender.com/docs` to see the API page.
7. In **Environment**, delete `INITIAL_ADMIN_PASSWORD` after the first
   successful startup, then use **Manual Deploy** → **Deploy latest commit**.
   The administrator remains in PostgreSQL, but the password is no longer
   stored in Render settings.

## 3. Deploy the dashboard (Vercel)

1. In Vercel, select **Add New** → **Project**.
2. Import the same GitHub repository.
3. In **Configure Project**, set these exact values:

   | Setting | Value |
   | --- | --- |
   | Framework Preset | `Vite` |
   | Root Directory | `.` (the repository root) |
   | Build Command | Leave the detected `cd dashboard && npm install && npm run build` value. |
   | Output Directory | `dashboard/dist` |

4. Before selecting Deploy, open **Environment Variables** and add:

   | Key | Value |
   | --- | --- |
   | `VITE_API_BASE_URL` | `https://YOUR-RENDER-SERVICE.onrender.com/api/v1` |

   Replace `YOUR-RENDER-SERVICE` with the actual public Render service name.
   Do not put a trailing slash on this value.
5. Select **Deploy**. When it completes, Vercel gives you a URL such as
   `https://demandiq-ai.vercel.app`.

## 4. Allow the dashboard to call the API

1. Return to Render → `demandiq-api` → **Environment**.
2. Replace `CORS_ORIGINS` with the exact Vercel URL, for example:

   ```text
   https://demandiq-ai.vercel.app
   ```

   If you want local development to continue working too, use a comma-separated
   value:

   ```text
   https://demandiq-ai.vercel.app,http://localhost:5173
   ```

3. Save the change. Render redeploys automatically; if it does not, use
   **Manual Deploy** → **Deploy latest commit**.
4. Visit the Vercel URL, sign in using the administrator account created in
   step 2, and verify these actions:
   - Dashboard and product list load.
   - A forecast can be generated.
   - A CSV can be previewed and confirmed.
   - A small inventory adjustment appears in the product history.

## Later updates

Push changes to the `main` branch. Render and Vercel automatically deploy the
new version. If the change adds a database migration, Render runs it before
starting the new API version.

## Important free-tier limits

- Render stops an inactive free backend after 15 minutes. The next visit can
  take about a minute while it starts again.
- Render's free filesystem is temporary. A confirmed CSV upload and a model
  trained through the dashboard are available while the service remains up,
  but the uploaded file/model artifact is reset after the backend restarts or
  sleeps. The original sample data and model stored in Git are restored.
- The PostgreSQL records themselves persist in Neon. For a real business
  deployment, move uploaded files and trained-model artifacts to persistent
  object storage before relying on those features.
- This setup is for a demo or portfolio project. Before accepting real
  customer data, add backups, monitoring, secure password reset, rate limits,
  and a paid/persistent hosting plan.

## If something fails

- **Vercel shows network error or login fails:** confirm `VITE_API_BASE_URL`
  uses `https`, ends in `/api/v1`, and `CORS_ORIGINS` on Render exactly matches
  the Vercel domain (no trailing slash).
- **Render says database connection failed:** paste the Neon connection string
  again as a single line, without quotation marks or spaces.
- **Render build succeeds but the service does not start:** open its deploy
  logs. The migration runs first, so the first failure after `alembic upgrade
  head` is the useful error to copy.
- **The first request is slow:** this is expected when a Render free service
  has been idle.
