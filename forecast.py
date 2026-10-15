#!/usr/bin/env python3
"""A local ledger for one forecast and one private explanation per Metaculus post."""

import argparse
import fcntl
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

BASE = "https://www.metaculus.com/api"
FIELDS = {"binary": "probability_yes", "multiple_choice": "probability_yes_per_category",
          "numeric": "continuous_cdf", "discrete": "continuous_cdf"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    pending = path.with_suffix(".pending")  # Durable transaction staging, beside its ledger.
    with pending.open("w", encoding="utf-8") as out:
        os.chmod(pending, 0o600)
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.flush()
        os.fsync(out.fileno())
    os.replace(pending, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def api(path, data=None):
    token = os.environ.get("METACULUS_TOKEN")
    require(token, "Set METACULUS_TOKEN to the primary bot's API token.")
    body = None if data is None else json.dumps(data, allow_nan=False).encode()
    request = Request(BASE + path, data=body, headers={
        "Authorization": "Token " + token, "Content-Type": "application/json"})
    with build_opener(ProxyHandler({})).open(request, timeout=30) as response:
        raw = response.read()
    return json.loads(raw) if raw else None


def payload(question, prediction):
    kind = question.get("type")
    require(kind in FIELDS, "Supported question types: " + ", ".join(FIELDS))
    field = FIELDS[kind]
    require(isinstance(prediction, dict) and set(prediction) == {"type", field},
            f"Prediction requires exactly type and {field}.")
    require(prediction["type"] == kind, "Prediction type must match the question.")
    value = prediction[field]
    if kind == "binary":
        require(number(value) and 0.001 <= value <= 0.999, "Binary probability: 0.001–0.999.")
    elif kind == "multiple_choice":
        options = question.get("options")
        require(isinstance(options, list) and len(options) >= 2, "Question options required.")
        require(isinstance(value, dict) and set(value) == set(options), "Supply every current option exactly.")
        require(all(number(p) and 0.001 <= p <= 0.999 for p in value.values()),
                "Option probabilities: 0.001–0.999.")
        require(math.isclose(sum(value.values()), 1, rel_tol=0, abs_tol=1e-9), "Probabilities must sum to 1.")
    else:
        scaling = question.get("scaling") or {}
        n = scaling.get("inbound_outcome_count") or question.get("inbound_outcome_count")
        if n is None and kind == "numeric":
            n = 200
        require(type(n) is int and n > 0, "Positive inbound_outcome_count required.")
        require(isinstance(value, list) and len(value) == n + 1, f"CDF requires {n + 1} values.")
        require(all(number(p) and 0 <= p <= 1 for p in value), "CDF values must be finite probabilities.")
        value = [round(p, 10) for p in value]
        # Match ForecastWriteSerializer: ten-place CDF, nine-place PMF, 40/n cap.
        steps = [round(b - a, 9) for a, b in zip(value, value[1:])]
        require(all(round(0.01 / n, 9) <= step <= 40 / n for step in steps),
                f"CDF increments must be within [{round(0.01 / n, 9)}, {40 / n}].")
        lower, upper = question.get("open_lower_bound"), question.get("open_upper_bound")
        require(type(lower) is bool and type(upper) is bool, "Explicit open-bound flags required.")
        require(value[0] >= 0.001 if lower else value[0] == 0, "CDF lower boundary failed.")
        require(value[-1] <= 0.999 if upper else value[-1] == 1, "CDF upper boundary failed.")
        grid = scaling.get("continuous_range")
        require(grid is None or len(grid) == len(value), "CDF must match continuous_range length.")
    return {"question": question["id"], "source": "api", field: value}


def forecast_values(question, data):
    value = data[FIELDS[question["type"]]]
    if question["type"] == "binary":
        return [1 - value, value]
    if question["type"] == "multiple_choice":
        return [value[option] for option in question["options"]]
    return value


def latest_values(question):
    require("my_forecasts" in question, "Authenticated my_forecasts field required.")
    mine = question["my_forecasts"]
    require(mine is None or isinstance(mine, dict), "Unexpected my_forecasts structure.")
    latest = (mine or {}).get("latest")
    if latest is None:
        return None
    require(isinstance(latest, dict) and isinstance(latest.get("forecast_values"), list),
            "待远端核对: latest forecast_values structure.")
    return latest["forecast_values"]


def poll(root, tournaments):
    found = {}
    for tournament in tournaments:
        offset = 0
        while True:
            query = urlencode({"tournaments": tournament, "statuses": "open", "limit": 100,
                               "offset": offset, "forecast_type": ",".join(FIELDS),
                               "include_description": "true", "order_by": "-hotness"})
            posts = api("/posts/?" + query)["results"]
            for post in posts:
                q = post.get("question") or {}
                if q.get("type") in FIELDS and q.get("status") == "open":
                    save(root / "posts" / f"{post['id']}.json", post)
                    receipt = root / "submissions" / f"{post['id']}.json"
                    record = read(receipt) if receipt.exists() else None
                    latest = (q.get("my_forecasts") or {}).get("latest")
                    if record and record["comment"] == "sent" or latest and record is None:
                        continue
                    found[post["id"]] = {"post": post["id"], "question": q["id"], "type": q["type"],
                                         "title": q["title"], "closes": q.get("scheduled_close_time"),
                                         "action": "resume" if record else "forecast"}
            if len(posts) < 100:
                break
            offset += len(posts)
    return list(found.values())


def submit(root, post_id, prediction, explanation):
    require(isinstance(explanation, str) and explanation.strip(), "A nonempty explanation is required.")
    post = api(f"/posts/{post_id}/")
    require(post.get("id") == post_id, "Post ID mismatch.")
    question = post.get("question") or {}
    data = payload(question, prediction)
    expected = forecast_values(question, data)
    save(root / "posts" / f"{post_id}.json", post)
    path = root / "submissions" / f"{post_id}.json"
    record = read(path) if path.exists() else {"post": post_id, "payload": data,
        "explanation": explanation, "forecast": "new", "comment": "new"}
    require(record["payload"] == data and record["explanation"] == explanation,
            "Use the original recorded prediction and explanation for this post.")
    actual = latest_values(question)
    if actual is not None:
        require(len(actual) == len(expected) and all(number(a) and abs(a - b) <= 1e-9
                for a, b in zip(actual, expected)), "待远端核对: existing forecast differs from the recorded values.")
        record["forecast"] = "sent"
        save(path, record)
    else:
        require(record["forecast"] == "new", "待远端核对: forecast send recorded; latest is empty.")
        require(question.get("status") == "open", "Question is closed; forecast stopped.")
        record["forecast"] = "pending"
        record["forecast_attempt_at"] = datetime.now(timezone.utc).isoformat()
        save(path, record)
        try:
            record["forecast_receipt"] = api("/questions/forecast/", [data])
        except Exception as error:
            record["error"] = "待远端核对: " + str(error)
            save(path, record)
            raise RuntimeError(record["error"]) from error
        record["forecast"] = "sent"
        save(path, record)
    if record["comment"] == "sent":
        return record
    require(record["comment"] == "new", "待远端核对: comment send recorded; inspect the comments API.")
    record["comment"] = "pending"
    record["comment_attempt_at"] = datetime.now(timezone.utc).isoformat()
    save(path, record)
    try:
        record["comment_receipt"] = api("/comments/create/", {"on_post": post_id,
            "text": explanation, "parent": None, "included_forecast": True, "is_private": True})
    except Exception as error:
        record["error"] = "待远端核对: " + str(error)
        save(path, record)
        raise RuntimeError(record["error"]) from error
    record["comment"] = "sent"
    record.pop("error", None)
    save(path, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path, help="Private state directory outside the repository")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("poll").add_argument("tournaments", nargs="+")
    for command in ("show", "submit"):
        sub = commands.add_parser(command)
        sub.add_argument("post", type=int)
        if command == "submit":
            sub.add_argument("prediction", type=Path)
            sub.add_argument("explanation", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    args.state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.command != "poll":
        require(args.post > 0, "Post ID must be positive.")
    # ponytail: one state-wide writer; use per-post locks if parallel throughput becomes necessary.
    with (args.state / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == "poll":
            result = poll(args.state, args.tournaments)
        elif args.command == "show":
            path = args.state / "submissions" / f"{args.post}.json"
            result = {"post": read(args.state / "posts" / f"{args.post}.json"),
                      "submission": read(path) if path.exists() else None}
        else:
            result = submit(args.state, args.post, read(args.prediction),
                            args.explanation.read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
