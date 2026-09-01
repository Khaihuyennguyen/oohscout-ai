import uuid
import psycopg
from psycopg.rows import dict_row

from oohscout.project import Corridor, Candidate
from oohscout.security import check_sql_safety, sanitize_error

# ==============================================================================
# Safe Data Writers
# ==============================================================================
def save_corridor(conn: psycopg.Connection, corridor_json: dict) -> uuid.UUID:
    """
    Parses raw JSON through the Pydantic Bouncer and inserts it safely.
    """
    # 1. The Bouncer (Validates the JSON)
    corridor = Corridor(**corridor_json)
    
    # 2. Safe Execution (Parameter binding prevents SQL injection)
    query = """
        INSERT INTO corridors (id, name, geometry, created_at)
        VALUES (%(id)s, %(name)s, %(geometry)s, %(created_at)s)
        RETURNING id;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, corridor.model_dump())
            result = cur.fetchone()
            conn.commit()
            return result[0]
    except Exception as e:
        conn.rollback()
        raise Exception(sanitize_error(str(e)))

def save_candidate(conn: psycopg.Connection, candidate_json: dict) -> uuid.UUID:
    """
    Parses raw JSON through the Pydantic Bouncer and inserts it safely.
    """
    # 1. The Bouncer (Validates the JSON, blocks 'LEGAL')
    candidate = Candidate(**candidate_json)
    
    # 2. Safe Execution
    query = """
        INSERT INTO candidates (id, corridor_id, parcel_id, geometry, regulatory_status, setback_distance_ft)
        VALUES (%(id)s, %(corridor_id)s, %(parcel_id)s, %(geometry)s, %(regulatory_status)s, %(setback_distance_ft)s)
        RETURNING id;
    """
    try:
        with conn.cursor() as cur:
            # We dump the model to a dictionary to pass to psycopg
            data = candidate.model_dump()
            # Enums must be extracted to strings for psycopg
            data['regulatory_status'] = data['regulatory_status'].value
            
            cur.execute(query, data)
            result = cur.fetchone()
            conn.commit()
            return result[0]
    except Exception as e:
        conn.rollback()
        raise Exception(sanitize_error(str(e)))

# ==============================================================================
# AI Custom Analytics
# ==============================================================================
def execute_agent_sql(conn: psycopg.Connection, query: str) -> list[dict]:
    """
    Allows the AI to execute custom analytics queries, strictly guarded
    against schema destruction.
    """
    # 1. The Guardrail (Blocks DROP/ALTER/TRUNCATE)
    try:
        check_sql_safety(query)
    except ValueError as e:
        raise ValueError(f"Agent SQL blocked by security layer: {e}")
        
    # 2. Execution
    try:
        # We use dict_row so the AI gets back clean JSON-like dictionaries
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query)
            
            # If it's a SELECT or RETURNING query, fetch results
            if cur.description:
                results = cur.fetchall()
            else:
                results = []
                
            conn.commit()
            return results
    except Exception as e:
        conn.rollback()
        raise Exception(sanitize_error(str(e)))
