from fastapi import Request
from fastapi.responses import JSONResponse
from oohscout.security import sanitize_error

async def global_exception_handler(request: Request, exc: Exception):
    """
    Acts as a global net to catch any unhandled server crashes.
    Intercepts the error, scrubs any passwords, and returns a safe 500 response.
    """
    # 1. Convert the crashed exception into a string
    raw_error_message = str(exc)
    
    # 2. Scrub the string using our security guardrail
    safe_error_message = sanitize_error(raw_error_message)
    
    # 3. Return a clean HTTP 500 response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": safe_error_message
        }
    )
