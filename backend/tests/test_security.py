"""Tests for oohscout.security — enforces CLAUDE.md rule 11 (V2 §S8).

Rule 11: Every LLM-supplied SQL must pass check_sql_safety().
         SELECT / WITH only. Reject INSERT/UPDATE/DELETE/CREATE/DROP/
         ALTER/TRUNCATE/etc. — including inside CTEs and after masking
         string literals.

Run:
    uv run pytest backend/tests/test_security.py -v
"""
from __future__ import annotations

import pytest

from oohscout.security import check_sql_safety


# ---------- SELECT / WITH — must be allowed ----------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select * from candidates",
        "  SELECT id, name FROM corridors WHERE id = 5  ",
        "SELECT id, name FROM corridors;",
        "WITH recent AS (SELECT * FROM candidates WHERE created_at > NOW() - INTERVAL '7 days') SELECT * FROM recent",
        "-- header comment\nSELECT 1",
        "/* block\n   comment */ SELECT 1",
        # Forbidden keyword appearing only inside a string literal is fine.
        "SELECT 'DROP TABLE users' AS not_a_command",
        # SQL-style '' escape inside a literal must not leak the keyword out.
        "SELECT 'it''s a DROP' AS quote_escape",
    ],
)
def test_read_only_queries_pass(sql: str) -> None:
    check_sql_safety(sql)  # must not raise


# ---------- INSERT / UPDATE / DELETE — must be blocked ----------

@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO candidates (id) VALUES (1)",
        "insert into candidates (id) values (1)",
        "UPDATE candidates SET score = 0",
        "DELETE FROM candidates WHERE id = 1",
        "MERGE INTO candidates USING staging ON candidates.id = staging.id WHEN MATCHED THEN UPDATE SET score = staging.score",
    ],
)
def test_writes_blocked(sql: str) -> None:
    with pytest.raises(ValueError):
        check_sql_safety(sql)


# ---------- Schema mutations — must be blocked ----------

@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE evil (id int)",
        "DROP TABLE candidates",
        "ALTER TABLE candidates ADD COLUMN pwned text",
        "TRUNCATE candidates",
        "GRANT ALL ON candidates TO public",
        "REVOKE ALL ON candidates FROM oohscout_ro",
        "COPY candidates FROM '/tmp/attack.csv'",
        "VACUUM candidates",
    ],
)
def test_schema_and_permission_mutations_blocked(sql: str) -> None:
    with pytest.raises(ValueError):
        check_sql_safety(sql)


# ---------- Sneaky attacks — must all be blocked ----------

def test_multi_statement_blocked() -> None:
    with pytest.raises(ValueError, match="multiple statements"):
        check_sql_safety("SELECT 1; DROP TABLE candidates")


def test_write_inside_cte_blocked() -> None:
    # WITH-prefixed statement must still be scanned for forbidden keywords.
    sql = (
        "WITH inserted AS ("
        "  INSERT INTO candidates (id) VALUES (1) RETURNING id"
        ") SELECT * FROM inserted"
    )
    with pytest.raises(ValueError, match="INSERT"):
        check_sql_safety(sql)


def test_comment_hidden_write_blocked() -> None:
    # A comment cannot smuggle SELECT-prefix past the head check.
    with pytest.raises(ValueError):
        check_sql_safety("-- SELECT 1\nDROP TABLE candidates")


def test_session_mutation_blocked() -> None:
    with pytest.raises(ValueError):
        check_sql_safety("SET statement_timeout = 0")


def test_do_block_blocked() -> None:
    with pytest.raises(ValueError):
        check_sql_safety("DO $$ BEGIN DROP TABLE candidates; END $$")


def test_leading_whitespace_does_not_bypass() -> None:
    with pytest.raises(ValueError):
        check_sql_safety("   DELETE FROM candidates")
