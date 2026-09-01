import os
import hmac
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Look for 'X-API-Token' in the request headers. 
# auto_error=False allows us to handle the missing token manually with a custom message.
api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)

def verify_token(api_key: str = Security(api_key_header)) -> str:
    """
    FastAPI Dependency to verify the incoming request token against the server's expected token.
    Uses hmac.compare_digest on bytes to prevent timing attacks.
    """
    # 1. Fetch the true token from the environment (fallback to 'dev-secret' for local testing)
    expected_token = os.environ.get("OOHSCOUT_API_TOKEN", "dev-secret-token")
    
    # 2. Check if the user even provided a token
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Token header.",
        )

    # 3. Secure comparison
    # We convert both strings to bytes to use compare_digest safely
    try:
        expected_bytes = expected_token.encode("utf-8")
        provided_bytes = api_key.encode("utf-8")
    except UnicodeEncodeError:
        # If the token contains invalid characters that can't be encoded, reject it immediately
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format.",
        )

    if not hmac.compare_digest(expected_bytes, provided_bytes):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-API-Token.",
        )

    # If it passes, return the valid token string
    return api_key
