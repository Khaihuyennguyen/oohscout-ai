# Building OOHScout: Step 2 - The Security Guardrails
*Date: August 31, 2026*

When giving an AI Agent the power to run SQL queries or fetch data from the internet, you open up potential security holes. Even if the AI isn't malicious, a user might try to trick the AI into doing something dangerous (known as "prompt injection").

To combat this, we borrowed three specific guardrail patterns from the GeoLibre architecture and implemented them into our foundation via a `security.py` file. This ensures our AI operates inside a perfectly safe sandbox.

## 1. The SSRF Guard (`assert_public_url`)
Server-Side Request Forgery (SSRF) happens when a malicious user tricks the server into making requests to internal or restricted network resources.

If the OOHScout AI Agent decides it needs to download a dataset from a website, it will fetch that URL. To prevent it from fetching `http://localhost:5432` or an internal AWS metadata endpoint:
* We built a function that resolves the hostname of every URL the AI tries to visit into an IP address.
* It checks if the IP is a loopback (`127.0.0.x`), private (`10.x`, `192.168.x`), or link-local address.
* If a restricted IP is detected, it blocks the request immediately and throws an error, completely neutralizing network scanning attempts.

## 2. The SQL Safety Net (`check_sql_safety`)
In OOHScout, the database is the absolute source of truth. The AI is allowed to write raw `INSERT` and `UPDATE` statements to the database (secured via PostgreSQL dynamic roles). However, we added a "belt and suspenders" regex guard as an extra layer of defense.

* This function scans the AI's SQL text *before* it gets sent to the database. 
* It masks out string literals (so the word "drop" inside a text field doesn't trigger a false alarm).
* It scans for forbidden, schema-altering keywords: `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`.
* If it detects these highly destructive commands, it blocks the query. This prevents the AI from accidentally deleting the candidate database.

## 3. The Error Sanitizer (`sanitize_error`)
If the database crashes or a connection fails, the software usually spits out an error log. Sometimes, that error log accidentally includes the database password (e.g., `Connection failed for postgresql://user:password@localhost`). 

If that error gets fed back to the AI or displayed on the screen, the password is leaked.
* We built a function that automatically scrubs passwords, API keys, and sensitive URLs out of error messages before they are ever returned to the user or the agent context.

By building these three guards *first*, we can confidently give the AI Agent its tools later in the process.
