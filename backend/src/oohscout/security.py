import re
import socket
import ipaddress
from urllib.parse import urlparse

# ==============================================================================
# 1. SSRF Guard
# ==============================================================================
def assert_public_url(url: str) -> None:
    """
    Validates that a URL resolves to a public, globally routable IP address.
    Blocks the AI from fetching data from localhost, private networks, or AWS metadata.
    """
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"Invalid URL provided: {url}")
        
    try:
        # Resolve the hostname to all its IP addresses
        addr_infos = socket.getaddrinfo(parsed.hostname, parsed.port or 80)
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {parsed.hostname}")
        
    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        ip = ipaddress.ip_address(ip_str)
        
        # Check against private, loopback, and link-local ranges
        if ip.is_loopback:
            raise ValueError(f"SSRF Blocked: URL resolves to loopback IP ({ip})")
        if ip.is_private:
            raise ValueError(f"SSRF Blocked: URL resolves to private IP ({ip})")
        if ip.is_link_local:
            raise ValueError(f"SSRF Blocked: URL resolves to link-local IP ({ip})")

# ==============================================================================
# 2. SQL Safety Net — read-only confinement (CLAUDE.md rule 11 / V2 §S8)
# ==============================================================================
# SELECT and WITH are the only permitted top-level statements. Everything that
# can mutate rows, schema, permissions, or session state is rejected — including
# when hidden inside a CTE, a trailing statement, or a comment.

# `'…'` with SQL-style `''` escaping. Two adjacent single quotes stay inside the
# literal so `'it''s a DROP'` doesn't leak `DROP` after masking.
_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

_FORBIDDEN_SQL_KW = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|MERGE|UPSERT|REPLACE"
    r"|CREATE|DROP|ALTER|TRUNCATE|RENAME|COMMENT"
    r"|GRANT|REVOKE|SECURITY"
    r"|COPY|IMPORT|EXPORT|ATTACH|DETACH|INSTALL|LOAD"
    r"|VACUUM|ANALYZE|CLUSTER|REINDEX|CHECKPOINT|PRAGMA"
    r"|LISTEN|NOTIFY|UNLISTEN"
    r"|SET|RESET|DISCARD|LOCK"
    r"|DO|CALL|EXECUTE|PREPARE|DEALLOCATE"
    r")\b",
    re.IGNORECASE,
)


def check_sql_safety(sql: str) -> None:
    """
    Raise ValueError unless ``sql`` is a single read-only SELECT/WITH query.

    The AI is allowed to run analytics. It is not allowed to write rows,
    change schema, grant permissions, mutate session state, or chain a
    second statement onto a read.
    """
    # 1. Mask string literals and comments so their contents never trigger.
    cleaned = _STRING_LITERAL_RE.sub("''", sql)
    cleaned = _BLOCK_COMMENT_RE.sub(" ", cleaned)
    cleaned = _LINE_COMMENT_RE.sub(" ", cleaned)

    # 2. Statement must start with SELECT or WITH.
    head = cleaned.strip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        raise ValueError(
            "Unsafe SQL: only SELECT and WITH queries are permitted."
        )

    # 3. Reject multi-statement payloads (`SELECT 1; DROP TABLE t`).
    #    A single trailing semicolon is fine; anything after it is not.
    trailing = head.rstrip().rstrip(";").rstrip()
    if ";" in trailing:
        raise ValueError(
            "Unsafe SQL: multiple statements are not permitted."
        )

    # 4. Reject any write/DDL/session keyword anywhere — catches writes
    #    inside a CTE like `WITH x AS (INSERT ... RETURNING ...) SELECT ...`.
    match = _FORBIDDEN_SQL_KW.search(cleaned)
    if match:
        raise ValueError(
            f"Unsafe SQL: '{match.group(1).upper()}' is not permitted "
            f"(SELECT/WITH read-only queries only)."
        )

# ==============================================================================
# 3. Error Sanitizer
# ==============================================================================
# Matches typical postgresql connection strings: postgresql://user:PASSWORD@host:port/db
_POSTGRES_CREDS_RE = re.compile(
    r'(?P<prefix>postgres(?:ql)?://[^:]+:)(?P<password>[^@]+)(?P<suffix>@)'
)

def sanitize_error(error_msg: str) -> str:
    """
    Scrubs database passwords from error messages to prevent credential leakage 
    if an error bubbles up to the AI or the user interface.
    """
    if not isinstance(error_msg, str):
        error_msg = str(error_msg)
        
    # Replace the captured <password> group with ***
    clean_msg = _POSTGRES_CREDS_RE.sub(r'\g<prefix>***\g<suffix>', error_msg)
    return clean_msg
