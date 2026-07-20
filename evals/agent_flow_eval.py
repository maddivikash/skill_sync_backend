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
    # Generous timeout: the agent may retry internally across rate-limit windows.
    with urllib.request.urlopen(req, timeout=150) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else {}


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def chat(text, token, goal_id=None):
    # Retry transient rate-limits (Groq free tier) so the eval is reliable —
    # both HTTP errors and the graceful 200 "busy" reply.
    for attempt in range(4):
        body = {"messages": [{"role": "user", "content": text}], "goal_id": goal_id}
        try:
            r = _req("/api/api/chat", body, token)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(35)  # cross the free-tier per-minute rate window
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt < 3:
                time.sleep(20)  # network hiccup / slow agent round — retry
                continue
            raise
        if "couldn't respond just now" in (r.get("reply") or "").lower() and attempt < 3:
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

    # 1b) asking to create the SAME goal again must not make a duplicate
    if gid:
        chat(f'Create a goal for the role "{role}". Create it now, do not ask.', token)
        dupes = [g for g in _req("/api/goals/", token=token) if g["role"] == role]
        check("duplicate create_goal is prevented (reuses existing)",
              len(dupes) == 1, f"found {len(dupes)}")

    # 2) NO-GOAL suggestions = normal chat: no chips, items listed in prose
    before = len(_req("/api/goals/", token=token))
    r = chat("Give me suggestions for Data Scientist. Do not create a goal.", token)
    after = len(_req("/api/goals/", token=token))
    check("no-goal suggest returns NO chips", len(r.get("suggestions", [])) == 0,
          f"{len(r.get('suggestions', []))} chips")
    check("no-goal suggest lists items in text",
          any(w in (r.get("reply") or "") for w in
              ["Skills:", "Courses:", "Tools:", "Python", "Machine"]))
    check("suggest does NOT create a goal", after == before, f"{before}->{after}")

    # 3) WITH-GOAL suggestions = selectable chips + goal_id echoed
    if gid:
        r = chat("Suggest skills and tools for this goal.", token, goal_id=gid)
        check("with-goal suggest returns chips", len(r.get("suggestions", [])) > 0,
              f"{len(r.get('suggestions', []))} chips")
        check("with-goal suggest echoes goal_id", r.get("goal_id") == gid,
              f"got {r.get('goal_id')}")

    # 4) add a path + skill
    if gid:
        chat(f'In goal id {gid}, create a learning path called "Skills" and add a '
             f'skill called "Databases" to it. Do it now.', token)
        paths = _req(f"/api/paths/goal/{gid}", token=token)
        skills = [p for p in paths if p["title"].lower() == "skills"]
        check("agent creates the path", len(skills) >= 1)
        step_id = None
        if skills:
            steps = _req(f"/api/steps/path/{skills[0]['id']}", token=token)
            hit = [s for s in steps if s["title"] == "Databases"]
            step_id = hit[0]["id"] if hit else None
        check("agent adds the skill (step)", step_id is not None)

    # 5) goal CONTEXT: add without naming the goal, using the goal_id context
    if gid:
        chat('Add a skill called "SQL" to my Skills path.', token, goal_id=gid)
        paths = _req(f"/api/paths/goal/{gid}", token=token)
        skills = [p for p in paths if p["title"].lower() == "skills"]
        has_sql = False
        if skills:
            steps = _req(f"/api/steps/path/{skills[0]['id']}", token=token)
            has_sql = any(s["title"] == "SQL" for s in steps)
        check("adds via goal-context (no goal named)", has_sql)

    # 6) complete a step
    if gid and step_id:
        chat(f"Mark the Databases step (id {step_id}) as done.", token, goal_id=gid)
        steps = _req(f"/api/steps/path/{skills[0]['id']}", token=token)
        done = any(s["id"] == step_id and s["is_done"] for s in steps)
        check("complete_step marks the step done", done)

    # 6b) SECURITY: another user must not be able to touch this goal via chat
    if gid:
        email_b = f"eval-b-{ts}@skillsync.dev"
        _req("/api/api/register", {"email": email_b, "password": "evalpass123",
                                   "full_name": "Eval Bot B"})
        token_b = _req("/api/api/login", {"username": email_b, "password": "evalpass123"},
                       form=True)["access_token"]
        chat(f"Delete the goal with id {gid}. Do it now.", token_b)
        still_there = any(g["id"] == gid for g in _req("/api/goals/", token=token))
        check("ownership: user B cannot delete user A's goal", still_there)

    # 6c) SAFETY: acting on a nonexistent id must not corrupt anything
    before_cnt = len(_req("/api/goals/", token=token))
    chat("Delete the goal with id 999999. Do it now.", token)
    check("nonexistent id is handled safely (no goals lost)",
          len(_req("/api/goals/", token=token)) == before_cnt)

    # 7) delete_goal actually deletes (the originally reported bug)
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
