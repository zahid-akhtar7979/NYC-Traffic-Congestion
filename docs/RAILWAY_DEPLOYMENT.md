# Deploy NYC Traffic Congestion on Railway

You have already connected your GitHub repo to Railway. Follow these steps to add databases, load data, and run the app.

**Quick order:** Add Postgres + MySQL → Add app from repo → Set variables → Deploy → Run schemas in dashboard → Run data loader via CLI → Generate domain → Open UI.

---

## 1. Create a project and add databases

1. In the **Railway dashboard**, open your project (or create one and connect the repo).
2. **Add PostgreSQL**
   - Click **+ New** → **Database** → **PostgreSQL** (or use **Ctrl/Cmd + K** and search "PostgreSQL").
   - Railway will create a Postgres service and expose `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`.
3. **Add MySQL**
   - Click **+ New** → **Database** → **MySQL**.
   - Railway will expose `MYSQLURL`, `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`.

---

## 2. Add and configure the app service

1. **Add the app from the same repo**
   - **+ New** → **GitHub Repo** → select your **NYC-Traffic-Congestion** repo.
   - Railway will add a new service that builds and runs from this repo.

2. **Configure the app service**
   - Open the **app service** (the one from the repo, not the databases).
   - Go to **Settings** (or **Variables**).

3. **Link database variables**
   - In **Variables**, add references so the app can connect to Postgres and MySQL:
     - **DATABASE_URL** = `${{Postgres.DATABASE_URL}}`  
       (Replace `Postgres` with the exact name of your Postgres service if different.)
     - **MYSQLHOST** = `${{MySQL.MYSQLHOST}}`
     - **MYSQLPORT** = `${{MySQL.MYSQLPORT}}`
     - **MYSQLUSER** = `${{MySQL.MYSQLUSER}}`
     - **MYSQLPASSWORD** = `${{MySQL.MYSQLPASSWORD}}`
     - **MYSQLDATABASE** = `${{MySQL.MYSQLDATABASE}}`  
       (Replace `MySQL` with the exact name of your MySQL service if different.)

4. **App-specific variable**
   - **PYTHONPATH** = `.`  
     (So imports like `backend` and `data_loader` work from repo root.)

5. **Web port**
   - Railway sets **PORT** automatically. The app is configured to use `PORT` in the start command.

6. **Start command (if not using Procfile)**
   - In **Settings** → **Deploy** → **Custom Start Command**, set:
     ```bash
     streamlit run frontend/dashboard.py --server.port=$PORT --server.address=0.0.0.0
     ```
   - If you use the **Procfile** in the repo, Railway will use that and you can leave start command blank.

7. **Root directory**
   - Leave **Root Directory** blank so the app runs from the repo root.

8. **Trigger a deploy**
   - Push to the connected branch or click **Deploy** so the app builds and starts.

---

## 3. Run database schemas (first-time setup)

After the first successful deploy, run the schema scripts **once** so the tables exist. The app image does not include `psql` or `mysql` clients, so use the Railway dashboard.

1. **PostgreSQL**
   - Open your **PostgreSQL** service in Railway.
   - Go to the **Data** or **Query** tab (or use **Connect** to get a client).
   - Copy the full contents of **`database/postgres_schema.sql`** from your repo.
   - Paste into the Query editor and run it. All dimension and fact tables (and indexes) will be created.

2. **MySQL**
   - Open your **MySQL** service in Railway.
   - Go to the **Query** (or equivalent) tab.
   - Copy the full contents of **`database/mysql_schema.sql`** from your repo.
   - Paste and run. All tables and indexes will be created.

If your Railway plan offers a **one-click connect** (e.g. TablePlus, DBeaver), you can run the same SQL files from your local machine using the provided connection details.

---

## 4. Load data (~1M CRZ + ~100K ridership)

Run the data loader once so the app has data to benchmark.

1. **From your repo (with Railway CLI and env from the app service):**
   ```bash
   cd /path/to/NYC-Traffic-Congestion
   railway link   # select project + app service
   railway run python data_loader/load_data.py
   ```
   This uses the app’s environment (including `DATABASE_URL` and `MYSQL*`) to connect to Postgres and MySQL and load data.

2. **Expected output**
   - Logs for download/clean/expand and inserts.
   - Final stats: rows per table, total time, rows/second.
   - If NYC Open Data is unreachable, the script uses fallback synthetic data.

3. **Optional: run again**
   - You can run `railway run python data_loader/load_data.py` again later to reload or add more data (e.g. after schema changes).

---

## 5. Open the app and run benchmarks

1. **Generate a public URL**
   - In the **app** service: **Settings** → **Networking** → **Generate Domain** (or **Public Networking**).
   - You’ll get a URL like `https://your-app.up.railway.app`.

2. **Open the dashboard**
   - Visit that URL in a browser. You should see the **NYC Congestion Pricing Analytics — Benchmark Dashboard**.

3. **Use the UI**
   - **Database Overview**: confirms Postgres and MySQL config.
   - **Run Benchmark**: runs the query benchmark and appends to `data/benchmark_results.csv` (stored in the container; new deploys start fresh unless you use a volume).
   - **Query Performance**, **Epoch vs Timestamp**, **Index Architecture**, **Concurrency**, **Query Planner**: run and view metrics as in local development.

---

## 6. Summary checklist

| Step | Action |
|------|--------|
| 1 | Add **PostgreSQL** and **MySQL** services in the project. |
| 2 | Add **service from GitHub** (this repo); set **Variables** (DATABASE_URL, MYSQL* from DB services, PYTHONPATH=.). |
| 3 | Set **start command** to Streamlit on `$PORT` (or use Procfile). Deploy. |
| 4 | Run **postgres_schema.sql** and **mysql_schema.sql** once (dashboard Query or CLI). |
| 5 | Run **`railway run python data_loader/load_data.py`** to load data. |
| 6 | **Generate domain** for the app and open the URL to use the UI and metrics. |

---

## 7. Troubleshooting

- **App won’t start**
  - Check **Variables** and that **DATABASE_URL** and **MYSQL*** are correctly referenced from the Postgres and MySQL services.
  - Ensure **Start Command** uses `$PORT` (e.g. `streamlit run frontend/dashboard.py --server.port=$PORT --server.address=0.0.0.0`).

- **“No database connection” or connection errors**
  - Confirm variable names match your Railway service names (e.g. `${{Postgres.DATABASE_URL}}` vs `${{PostgreSQL.DATABASE_URL}}`).
  - For MySQL, the app reads **MYSQLHOST**, **MYSQLPORT**, **MYSQLUSER**, **MYSQLPASSWORD**, **MYSQLDATABASE** (or **MYSQL_URL** if you add support).

- **Schema or data load fails**
  - Run schemas from the dashboard Query tabs if `railway run` doesn’t have `psql`/`mysql` in the image.
  - For data load, run `railway run python data_loader/load_data.py` from the repo root after a successful deploy.

- **Benchmark results disappear after redeploy**
  - The CSV is written inside the container. For persistence, you’d need a volume or external storage; the current setup is suitable for demo/testing.
