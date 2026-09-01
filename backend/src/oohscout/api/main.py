import os
import contextlib
import psycopg
from fastapi import FastAPI, HTTPException, Request
from psycopg.rows import dict_row

import sys
import asyncio

from oohscout.api.errors import global_exception_handler

# On Windows, psycopg requires the SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# The lifespan manager handles things that need to start up BEFORE the server 
# accepts traffic, and shut down AFTER the server stops.
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # Fetch the database URL from the environment (defaulting to a local test db)
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/oohscout")
    
    try:
        # In a massive production app, we would use psycopg_pool. 
        # For our OOHScout MVP, we establish a robust AsyncConnection.
        app.state.db_conn = await psycopg.AsyncConnection.connect(db_url, row_factory=dict_row)
        print("[OK] Database connection established.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        app.state.db_conn = None

    yield # This yields control back to FastAPI to run the server

    # --- SHUTDOWN ---
    if app.state.db_conn:
        await app.state.db_conn.close()
        print("[OK] Database connection closed.")

# Initialize the actual Web Server
app = FastAPI(
    title="OOHScout AI API",
    description="The secure backend for OOHScout spatial and AI workflows.",
    version="0.0.1",
    lifespan=lifespan
)

# Attach our PR Manager to intercept crashes
app.add_exception_handler(Exception, global_exception_handler)

# ==============================================================================
# Routes
# ==============================================================================

@app.get("/health")
async def health_check(request: Request):
    """
    A simple heartbeat endpoint to prove the server is running and 
    the database is reachable.
    """
    conn = request.app.state.db_conn
    
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection is not initialized.")
        
    try:
        # Run a tiny, harmless query just to prove the connection is alive
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 AS heartbeat;")
            result = await cur.fetchone()
            
        return {
            "status": "ok", 
            "database": "connected", 
            "heartbeat": result["heartbeat"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database connection failed.")
