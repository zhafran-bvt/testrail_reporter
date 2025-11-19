To deploy your application on Railway, follow these steps:

1.  **Create a Railway Account and Project:**
    *   Go to [Railway.app](https://railway.app/) and sign up or log in, preferably using your GitHub account.
    *   From your Railway dashboard, click "New Project".
    *   Select "Deploy from GitHub Repo" and connect your GitHub account if you haven't already.
    *   Choose the GitHub repository containing your Python application.

2.  **Configure Environment Variables:**
    *   After selecting your repository, Railway will start the deployment process.
    *   Navigate to your service's settings in the Railway dashboard and find the "Variables" section.
    *   Add the following environment variables, ensuring their values are correct:
        *   `TESTRAIL_BASE_URL`
        *   `TESTRAIL_USER`
        *   `TESTRAIL_API_KEY`

3.  **Monitor and Verify Deployment:**
    *   Railway will automatically build and deploy your application. You can monitor the build and deployment logs in the Railway dashboard.
    *   Once deployed, check the logs to ensure your server is running successfully.
    *   **Public URL**: To get a public URL, navigate to the "Networking" section under the "Settings" tab of your service and click "Generate Domain".
    *   **Important:** keep web concurrency at 1 (`--workers 1`). The background report queue runs inside the app process, so multiple Gunicorn workers will each have isolated job lists and you’ll see “Report job not found” when polling from another worker.
    *   Increase Gunicorn’s timeout if Railway overrides the Dockerfile/Procfile command. Reports with attachments regularly exceed 30 s; match the repo defaults (`--timeout 600 --graceful-timeout 120`) so workers aren’t killed mid-report.

Your existing `Procfile` and `Dockerfile` are already compatible with Railway, so no changes are needed for those files.
