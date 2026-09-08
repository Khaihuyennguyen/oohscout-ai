# Building OOHScout: Step 10 - The Brain (`SKILL.md`)
*Date: August 31, 2026*

We have reached the absolute final step of our foundational plumbing roadmap.

In the first 9 steps, we built a highly secure database (Phase 1), a web server to protect it (Phase 2), and a strict set of Tools and Sandboxes for the AI to use (Phase 3). 

However, if you turn the AI on right now, it is essentially an empty shell. It has tools, but it has no idea what its job is. 

**Step 10 is writing `skills/SKILL.md`.**

## What is a SKILL file?
In modern Agentic AI engineering, the `SKILL.md` file acts as the System Prompt (the Master Instruction Manual). It transforms a general-purpose AI (like Claude or ChatGPT) into a highly specialized expert. 

If you don't write this file, the AI will act like a helpful intern who asks a million questions. If you *do* write this file properly, the AI acts like a Senior Architect who works autonomously.

## What goes inside it?
A perfect `SKILL.md` file contains three things:

1. **The Persona:** We explicitly tell the AI: *"You are an elite Geospatial AI Engineer specializing in Out-of-Home (billboard) advertising in Texas."* This forces the AI's neural network to retrieve its best spatial and legal knowledge.
2. **The Workflow:** We tell it exactly *when* to use the tools we built in Step 9. *"First, read the zoning file using your read tool. Second, if it passes, use your database tool."*
3. **The Golden Rules:** We reiterate the core business logic. *"WARNING: Never use the word LEGAL. You are not a human lawyer. You may only use PASS, FAIL, or REVIEW."*

By hardcoding these instructions, we ensure that the AI Agent runs our exact OOHScout playbook every single time, without exception.
