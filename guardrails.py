"""Rule checks that run AFTER the AI step.

The AI only reads the request. These checks decide what is allowed,
so a wrong or tricked AI answer cannot give anyone extra access.
"""
from datetime import date

VAGUE_DATES = ["same day", "same date", "as above", "asap", "soon", "tbc", "tbd"]


def check_request(req: dict, policy: dict, today: date | None = None) -> list[str]:
    """Return a list of problems. An empty list means the request can go to approval."""
    today = today or date.today()
    problems = []

    # One person per request, so nobody gets dropped without a warning
    people = req.get("all_people_mentioned") or []
    if len(people) > 1:
        problems.append(f"Request mentions {len(people)} people ({', '.join(people)}). Send one request per person.")

    action = req.get("action")
    if action not in ("joiner", "leaver"):
        problems.append("Action is not clear (must be joiner or leaver).")

    name = (req.get("full_name") or "").strip()
    if len(name.split()) < 2:
        problems.append("Full name (first and last) is missing.")

    # Date check
    raw_date = req.get("date")
    try:
        when = date.fromisoformat(raw_date) if raw_date else None
    except ValueError:
        when = None
    date_text = (req.get("date_text") or "").strip().lower()
    if when is None:
        problems.append("Date is missing or not a real date.")
    elif not date_text or date_text not in (req.get("_request_text") or "").lower():
        problems.append("The date is not written in the request, so it may be a guess.")
    elif any(v in date_text for v in VAGUE_DATES) or req.get("date_is_clear") is False:
        problems.append(f"The date '{date_text}' depends on something not in the request. Ask for the real date.")
    elif action == "joiner" and when < today:
        problems.append(f"Start date {when} is in the past.")

    # Department and role must be on the approved list (least privilege)
    if action == "joiner":
        dept = req.get("department")
        role = req.get("role")
        roles = policy["departments"].get(dept)
        if roles is None:
            problems.append(f"Department '{dept}' is not on the approved list.")
        elif not role:
            problems.append(f"Role is missing for {dept}.")
        elif role not in roles:
            problems.append(f"Role '{role}' is not an approved role in {dept}.")

    # Any extra access is never auto-approved
    for item in req.get("extra_access") or []:
        if any(k in item.lower() for k in policy["blocked_keywords"]):
            problems.append(f"Privileged access requested ('{item}'). Blocked: needs a separate approval.")
        else:
            problems.append(f"Extra access requested ('{item}'). Not in the role template, so a manager must approve it separately.")

    return problems


def groups_for(req: dict, policy: dict) -> list[str]:
    return policy["departments"][req["department"]][req["role"]]


def clean_name(name: str) -> str:
    """Capitalise each word but keep the rest (O'brien -> O'brien, park -> Park, McDonald stays)."""
    return " ".join(w[:1].upper() + w[1:] for w in name.split())
