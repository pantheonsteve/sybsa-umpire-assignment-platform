# Deployment Instructions for Render

## Migrating Data from SQLite to PostgreSQL

If you have existing data in SQLite that you want to preserve:

### Step 1: Export your SQLite data
```bash
python migrate_data.py
```
This creates JSON backup files of all your data.

### Step 2: Deploy to Render
Follow the deployment steps below to create your PostgreSQL database.

### Step 3: Import data to PostgreSQL
After deployment, get your database URL from Render:
1. Go to Render dashboard → Your database → "Connect" section
2. Copy the "External Database URL"
3. Run locally:
```bash
export DATABASE_URL='<paste-url-here>'
python migrate_data_import.py
```

### Step 4: Clean up
```bash
rm backup_assignments_*.json
```

## Steps to Deploy with PostgreSQL

1. **Push your code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Configure PostgreSQL for production"
   git push origin main
   ```

2. **Deploy on Render**
   - Go to https://render.com and sign in
   - Click "New +" and select "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect your `render.yaml` file
   - Click "Apply" to create both:
     - A PostgreSQL database (free tier)
     - Your web service

3. **The deployment will automatically:**
   - Create a PostgreSQL database named `umpireassigner`
   - Set the DATABASE_URL environment variable
   - Run migrations on each deployment
   - Preserve your data between deployments

## Important Notes

- Your data will now persist between deployments (unlike SQLite)
- The free PostgreSQL tier includes:
  - 1 GB storage
  - 97 days of backups
  - Automatic daily backups
- The safety check in settings.py will prevent accidental SQLite usage in production

## Verifying the Setup

After deployment, you can verify PostgreSQL is being used:
1. Go to your Render dashboard
2. Click on your web service
3. Go to "Environment" tab
4. Confirm DATABASE_URL is set (it will be automatically configured)

## Troubleshooting

If you see the "SQLite cannot be used in production" error:
- Check that DATABASE_URL is properly set in Render's environment variables
- The URL should start with `postgresql://` or `postgres://`