# Building OOHScout: Steps 6 & 7 - API Security & Error Handling
*Date: August 31, 2026*

With the FastAPI server acting as the main lobby in Step 5, we needed to ensure that no unauthorized users or rogue processes could access the database. We accomplished this in two steps: securing the front door, and managing internal crises.

## Step 6: The Keycard Reader (`auth.py`)
If you put a server on a network, anyone can theoretically try to talk to it. To lock the door, we built `api/auth.py`.

* **How it works:** It forces every incoming request to include a specific header: `X-API-Token`.
* **Timing Attack Prevention:** A naive way to check a password is `if provided_token == real_token`. However, hackers can measure the milliseconds it takes for that check to fail, allowing them to guess the password character by character (a "Timing Attack"). 
* We used the pattern from GeoLibre: `hmac.compare_digest()`. This function takes the exact same amount of time to compute whether the password is right or wrong, completely neutralizing brute-force timing attacks. If the token is wrong, it instantly throws a `401 Unauthorized` error.

## Step 7: The PR Manager (`errors.py`)
If something goes terribly wrong—for example, if the PostgreSQL database crashes or a connection times out—the Python server will crash. 

When Python servers crash, they usually dump a "stack trace" (a massive log of what went wrong) directly to the screen or the API response. This stack trace often includes the database connection string (e.g., `Failed to connect to postgresql://user:MySecretPassword@localhost`). If the AI sees this, your password is leaked.

* **How it works:** We build an "Exception Handler" in `api/errors.py`. 
* It acts like a PR Manager. Before any crash report is sent back to the user or the AI, it intercepts the error.
* It passes the error string through the `sanitize_error()` guardrail we built back in Step 2.
* It scrubs out any passwords and replaces them with `***`, returning a safe `500 Internal Server Error` response. 

Together, these two files ensure that hackers can't get in, and secrets can't get out.
