"""End-to-end eval for the AI coach's agentic flow.

Exercises the real /api/chat agent against a throwaway account and asserts the
DATABASE actually changed as claimed (catches hallucinated actions like
"I deleted it" when nothing happened).

Run:  ASCEND_API=https://ascenddaily.in python3 evals/agent_flow_eval.py
Exits non-zero if any check fails.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("ASCEND_API", "https://ascenddaily.in")
results = []


def _req(path, data=None, token=None, form=False, method=None):
    headers = {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    m = method or ("POST" if data is not None else "GET")
    req = urllib.request.Request(API + path, data=body, headers=headers, method=m)
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else {}


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def chat(text, token):
    # Retry transient rate-limits (Groq free tier) so the eval is reliable —
    # both HTTP errors and the graceful 200 "busy" reply.
    for attempt in range(4):
        try:
            r = _req("/api/api/chat", {"messages": [{"role": "user", "content": text}]}, token)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 3:
                time.sleep(35)  # cross the free-tier per-minute rate window
                continue
            raise
        if "handling a lot of requests" in (r.get("reply") or "").lower() and attempt < 3:
            time.sleep(35)
            continue
        time.sleep(3)  # gentle spacing between agent calls
        return r
    return {}


def main():
    ts = int(time.time())
    email = f"eval-{ts}@skillsync.dev"
    _req("/api/api/register", {"email": email, "password": "evalpass123", "full_name": "Eval Bot"})
    token = _req("/api/api/login", {"username": email, "password": "evalpass123"}, form=True)["access_token"]

    # 1) create_goal
    role = f"Eval Engineer {ts}"
    chat(f'Create a goal for the role "{role}". Create it now, do not ask.', token)
    goals = _req("/api/goals/", token=token)
    match = [g for g in goals if g["role"] == role]
    check("create_goal actually creates the goal", len(match) == 1, f"found {len(match)}")
    gid = match[0]["id"] if match else None

    # 2) suggest_for_role returns chips and does NOT create a goal
    before = len(_req("/api/goals/", token=token))
    r = chat("Get suggestions for Data Scientist. Do not create a goal.", token)
    after = len(_req("/api/goals/", token=token))
    check("suggest_for_role returns suggestions", len(r.get("suggestions", [])) > 0,
          f"{len(r.get('suggestions', []))} suggestions")
    check("suggest_for_role does NOT create a goal", after == before, f"{before}->{after}")

    # 3) add a path + skill
    if gid:
        chat(f'In goal id {gid}, create a learning path called "Skills" and add a '
             f'skill called "Databases" to it. Do it now.', token)
        paths = _req(f"/api/paths/goal/{gid}", token=token)
        skills = [p for p in paths if p["title"].lower() == "skills"]
        check("agent creates the path", len(skills) >= 1)
        has_step = False
        if skills:
            steps = _req(f"/api/steps/path/{skills[0]['id']}", token=token)
            has_step = any(s["title"] == "Databases" for s in steps)
        check("agent adds the skill (step)", has_step)

    # 4) delete_goal actually deletes (the reported bug)
    if gid:
        chat(f"Delete the goal with id {gid}. Do it now.", token)
        goals_after = _req("/api/goals/", token=token)
        check("delete_goal actually deletes the goal",
              all(g["id"] != gid for g in goals_after))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
