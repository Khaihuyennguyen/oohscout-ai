from pathlib import Path
from fastapi import HTTPException, status

# Define the absolute path to the sandbox (the data folder)
# We resolve it immediately so we have the canonical, absolute path.
BASE_DIR = Path(__file__).resolve().parent.parent / "data"

# Ensure the data directory actually exists on the hard drive
BASE_DIR.mkdir(parents=True, exist_ok=True)

# A strict list of file extensions the AI is FORBIDDEN from creating or modifying.
# This prevents the AI from generating executable scripts or overwriting our Python code.
FORBIDDEN_EXTENSIONS = {".py", ".sh", ".exe", ".bat", ".cmd", ".js"}

def resolve_path(requested_path: str) -> Path:
    """
    Takes a path requested by the AI and mathematically guarantees it resides 
    inside the safe data folder.
    """
    # 1. Combine the base directory with the requested path.
    # If requested_path is absolute (e.g., "C:/Windows"), this will behave dangerously
    # in standard string concatenation, but pathlib handles it by returning the absolute path.
    # However, to be ultra-safe against weird OS behaviors, we strip leading slashes.
    safe_request = requested_path.lstrip("/\\")
    
    # 2. Resolve the full path to eliminate any "../" tricks (Path Traversal attacks).
    target_path = (BASE_DIR / safe_request).resolve()
    
    # 3. The Ultimate Check: Is the target path actually inside our BASE_DIR?
    if not target_path.is_relative_to(BASE_DIR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Path Traversal Blocked: The AI attempted to access a file outside the sandbox."
        )
        
    return target_path

def assert_safe_extension(target_path: Path) -> None:
    """
    Checks the file extension of the target path to prevent the AI from 
    creating executable malware or overwriting system files.
    """
    # suffix returns the extension (e.g., '.py')
    if target_path.suffix.lower() in FORBIDDEN_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Block: The AI is strictly forbidden from writing {target_path.suffix} files."
        )
