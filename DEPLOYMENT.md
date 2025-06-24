# Deployment Guide (Cloud-Native)

[**English**](./DEPLOYMENT.md) | [**中文**](./DEPLOYMENT.zh-CN.md)

---

## 🇬🇧 English

This guide provides step-by-step instructions for deploying the full-stack AI Analyst application to Google Cloud Platform using a robust, cloud-native architecture.

### Deployment Strategy

We will use a modern and efficient combination of services:

* **Backend (Python/FastAPI)**: Deployed on **Cloud Run**, a serverless container platform that automatically scales and is highly cost-effective.
* **Frontend (React/TypeScript)**: Hosted on **Firebase Hosting**, which provides a global CDN for fast, low-latency content delivery.
* **Scheduled Tasks**: Managed by **Cloud Scheduler**, ensuring reliable and secure triggering of background jobs.

---

### Part 0: Prerequisites - Local Tools

Before starting, ensure you have the following tools installed on your local machine:

1.  **`gcloud` CLI (Google Cloud SDK)**: The command-line tool for interacting with Google Cloud.
    * Follow the [official installation guide](https://cloud.google.com/sdk/docs/install).
    * After installation, run `gcloud init` to log in and select your Google Cloud project.

2.  **Docker Desktop**: Needed to containerize our backend application.
    * Download and install from the [official Docker website](https://www.docker.com/products/docker-desktop/).

3.  **Firebase CLI**: The command-line tool for interacting with Firebase.
    * Install it globally by running: `npm install -g firebase-tools`.

---

### Part 1: Deploying the Backend to Cloud Run

This is the most critical part, where we package and launch our Python application.

#### Step 1.1: Prepare the Backend for Production

1.  **Install Gunicorn**: Gunicorn is a professional-grade application server for Python.
    ```bash
    # Navigate to your backend/ directory and activate the virtual environment
    cd backend
    pip install gunicorn
    pip freeze > requirements.txt # Regenerate requirements to include gunicorn
    ```

2.  **Finalize `Dockerfile`**: Ensure the `Dockerfile` in your `backend/` directory contains the following final version. This version is optimized for Cloud Run.

    ```dockerfile
    # Use the official Python 3.11 slim base image
    FROM python:3.11-slim

    # Set the working directory inside the container
    WORKDIR /code

    # Copy and install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade -r requirements.txt

    # Copy the entire 'app' directory with all source code
    COPY ./app ./app

    # Expose the port Cloud Run will provide
    EXPOSE 8080

    # The final command to run the application using gunicorn
    # -w 1 (a single worker) is crucial for in-memory schedulers or stateful apps.
    # The --timeout flag gives background tasks more time to complete.
    CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080", "--timeout", "90"]
    ```

#### Step 1.2: Build and Deploy

We will use a single `gcloud` command to build the Docker image, push it to Google's Artifact Registry, and deploy it to Cloud Run.

1.  **Enable Required Cloud APIs**: (Run this once per project)
    ```bash
    gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com appengine.googleapis.com
    ```

2.  **Run the One-Click Deploy Command**:
    * From your project's **root directory** (the one containing `frontend` and `backend`), run the following command.
    * Replace `[YOUR_PROJECT_ID]`, `[YOUR_GEMINI_API_KEY]`, and `[YOUR_GITHUB_TOKEN]`.

    ```bash
    gcloud run deploy ai-analyst-backend \
      --source ./backend \
      --platform=managed \
      --region=us-central1 \
      --allow-unauthenticated \
      --memory=1Gi \
      --set-env-vars="AI_API_KEY=[YOUR_GEMINI_API_KEY],GITHUB_TOKEN=[YOUR_GITHUB_TOKEN]"
    ```
    * **Note on Parameters**:
        * `--source ./backend`: Tells gcloud to build from the `backend` folder.
        * `--allow-unauthenticated`: Allows public access to your API so the frontend can call it.
        * `--memory=1Gi`: Allocates sufficient memory to prevent crashes.
        * `--set-env-vars`: Securely sets your secret keys in the cloud environment.

3.  **Save the URL**: After a few minutes, the command will complete and print the public **Service URL**. Copy and save this URL carefully.

---

### Part 2: Deploying the Frontend to Firebase Hosting

With the backend live, let's get the frontend online.

#### Step 2.1: Update API Endpoint

1.  Open your frontend code at `frontend/src/App.tsx`.
2.  Find the `API_BASE_URL` constant.
3.  Replace its value with the backend **Service URL** you saved from the previous step.
    ```typescript
    const API_BASE_URL = '[https://ai-analyst-backend-xxxxxxxx-uc.a.run.app](https://ai-analyst-backend-xxxxxxxx-uc.a.run.app)';
    ```

#### Step 2.2: Build and Deploy

1.  **Build the production-ready static files:**
    ```bash
    # Navigate to your frontend/ directory
    cd frontend
    npm run build
    ```

2.  **Initialize Firebase in your project:**
    ```bash
    firebase init hosting
    ```
    * **Answer the prompts as follows**:
        * `Please select an option:` -> **`Use an existing project`**
        * `Select a default Firebase project...:` -> Choose your Google Cloud project from the list.
        * `What do you want to use as your public directory?` -> Enter **`dist`**
        * `Configure as a single-page app...?` -> Enter **`y`** (Yes)
        * `Set up automatic builds...?` -> Enter **`n`** (No, we'll deploy manually for now)
        * `File dist/index.html already exists. Overwrite?` -> Enter **`N`** (No)

3.  **Deploy to the world!**
    ```bash
    firebase deploy
    ```
    After completion, it will give you a **Hosting URL**. This is your live application's public address.

---

### Part 3: Setting Up the Cloud Scheduler

This is the final step to make your application autonomous.

#### Step 3.1: Create the App Engine App (Run Once)

Cloud Scheduler requires an App Engine app in the project to determine its region.
```bash
# Choose a region close to you, e.g., us-central
gcloud app create --region=us-central
```

#### Step 3.2: Create the Scheduler Job

1.  **Open the [Google Cloud Scheduler Console](https://console.cloud.google.com/cloudscheduler)**.
2.  Click **"CREATE JOB"**.
3.  **Fill out the form**:
    * **Name**: `run-analysis-task`
    * **Region**: Select the same region as your Cloud Run service (e.g., `us-central1`).
    * **Frequency**: `*/10 * * * *` (This cron expression means "run every 10 minutes").
    * **Timezone**: Select your desired timezone.
    * **Target type**: **HTTP**
    * **URL**: Paste your backend's **Service URL** and append `/api/internal/run-task`.
    * **HTTP method**: **POST**
    * Click **"SHOW MORE"**.
    * **Auth header**: Select **"Add OIDC token"**.
    * **Service account**: Select the **"Compute Engine default service account"**.
    * **Headers**: Click "ADD HEADER".
        * Header name: `X-Cloud-Scheduler`
        * Header value: `true`
4.  Click **"CREATE"**.

#### Step 3.3: Force Run the First Task

1.  In the Cloud Scheduler job list, find `run-analysis-task`.
2.  Click the three-dot menu on the right and select **"Force run"**.
3.  You can now go to the **Cloud Run logs** to monitor the execution of your background task. Once it completes, refresh your frontend application, and you should see the initial data!

Congratulations! You have successfully deployed a production-grade, full-stack AI application.
