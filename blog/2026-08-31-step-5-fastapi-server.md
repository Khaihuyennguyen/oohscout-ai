# Building OOHScout: Step 5 - The Web Server (`api/main.py`)
*Date: August 31, 2026*

With our safe data vault (Phase 1) complete, we need a way for the outside world—specifically our AI Agent—to interact with it. 

Step 5 involves building a web server using **FastAPI**, a modern, high-performance web framework for Python. We place this inside `backend/src/oohscout/api/main.py`.

## The Role of `main.py`
Think of `main.py` as the main lobby of a secure building. It has three primary jobs:

### 1. Application Initialization
It boots up the FastAPI application and gives it a name (OOHScout AI API). This is the foundation that will eventually host all our secure routes and AI endpoints.

### 2. Database Lifecycle Management
A common mistake in app development is opening a new database connection every time a request comes in. This slows down the app and can crash the database. 
Instead, `main.py` handles the "Lifespan" of the app. When the server turns on, it opens a highly efficient **Connection Pool** to PostgreSQL. It keeps these connections warm and ready. When the server turns off, it cleanly closes them.

### 3. The Heartbeat (Health Check)
It provides a simple `GET /health` endpoint. This is a tiny route that returns `{"status": "ok"}`. It allows other systems (and us) to ping the server to ensure the database connection is alive and the server hasn't crashed, without actually executing any heavy logic.

By setting this up cleanly, we create a stable, fast environment that can handle hundreds of requests from the AI Agent without breaking a sweat.
