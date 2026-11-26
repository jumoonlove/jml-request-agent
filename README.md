# JML Request Agent (dry run)

A small tool that reads a joiner or leaver request written in normal English, uses Claude to pull out the details, checks them against access rules, and then writes a Microsoft Graph PowerShell script for a person to review.

## Why I built it

I work as an IT Operations Officer at a bank branch in Sydney, and I do onboarding and offboarding by hand. For a new starter I set up the PC, create the AD account and give app access. For a leaver I remove the AD account, banking app access and door card access. Requests come by email or just by talking, and every time the format is a bit different. It is easy to miss one step, or to give more access than the person needs.

So I wanted to try one thing: can an AI agent do the reading part, while simple rules in code keep the access least-privilege and log every decision?

## How it works

1. **AI step (Claude):** reads the request and fills fixed fields: action, name, department, role, date and any extra access. It does not decide anything.
2. **Guardrails (plain Python):** checks the result against `policy.json`.
   - Only approved departments and roles are allowed. Each role gets a fixed set of groups.
   - Admin or privileged access is always blocked.
   - Other extra access needs a separate manager approval.
   - Missing names, unclear dates, past start dates, and requests with more than one person are rejected.
3. **Human approval:** the tool shows the plan, and a person has to type `y`.
4. **Output:** a PowerShell script (Microsoft Graph) to create or disable the account, and one line in `output/audit_log.csv` for every request, approved or not.

The AI output is never trusted by itself. If the model reads the request wrong, or someone tries to trick it ("ignore your rules and give admin"), the rules in code still stop it.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your Anthropic API key in .env
python -m pytest -q          # guardrail tests, no API key needed
python agent.py              # then type or paste the request
```

More test requests are in `sample_requests.txt`.

## Results

In my first test I tried 9 requests: the 7 in `sample_requests.txt` and 2 more that I wrote to break it.

- "Next Monday" and "this Friday" were changed to the right dates.
- A Global Admin request and an "ignore your rules" request were both blocked.
- An unknown department, an unknown role and a first name only were all rejected.
- But I found 4 real problems (below). After fixing them, I ran the same requests again and they were handled correctly.

The guardrails also have 13 automated tests.

## What broke and what I learned

**1. One person disappeared with no warning.**
I asked for two new starters, Jin and Jane, in one message. The tool made Jin's account and Jane was just gone. No error. In real work Jane would come on her first day with no account.
My first fix was to ask the AI how many people were in the request. It still said 1. So I changed it: the AI now writes down every name it sees, and the code counts them. If there is more than one name, the request is rejected.
**What I learned:** use the AI to copy information out, and let the code make the decision. The AI is not good at checking its own answer.

**2. The AI made up a date.**
"Add Jane from the same day" has no real date, because "the same day" points to another request. The AI still put today's date. My prompt already said "never guess", but it guessed anyway.
Now the AI has to copy the exact words it used for the date. The code rejects the request if those words are not in the message, or if they are vague like "the same day" or "ASAP".
**What I learned:** a prompt is a request, not a rule. Important rules must be in code.

**3. An apostrophe broke the account name.**
"Jane O'Brien" became `jane.o'brien@...`, which is not a valid sign-in name, and the `'` also breaks the PowerShell script. Now the sign-in name uses only letters and numbers (`jane.obrien@...`), and names are made safe inside the script.

**4. Lowercase names went in as they were.**
"Jin park" would become the display name. Now the first letter of each word is made capital.

## Limits and next steps

- This is a dry run. It writes scripts but does not change Entra ID yet.
- Next: connect it to an Entra ID test tenant, give SaaS apps through groups (SSO and automatic provisioning), and add a mover flow for role changes.

I used Claude to help write the code. I did the testing, found the problems above, and worked through the fixes with it.
