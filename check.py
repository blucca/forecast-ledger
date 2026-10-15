#!/usr/bin/env python3
"""Run with: python -B check.py /path/to/workspace/temp"""

import copy
import sys
import tempfile
from pathlib import Path

import forecast as f


def fails(call):
    try:
        call()
    except (ValueError, RuntimeError):
        return
    raise AssertionError("Expected validation or pending-remote failure")


binary = {"id": 12, "type": "binary", "status": "open", "my_forecasts": None}
choice = {**binary, "type": "multiple_choice", "options": ["A", "B", "C"]}
numeric = {**binary, "type": "numeric", "open_lower_bound": True, "open_upper_bound": True,
           "scaling": {"inbound_outcome_count": 200}}
discrete = {**numeric, "type": "discrete", "open_lower_bound": False, "open_upper_bound": False,
            "scaling": {"inbound_outcome_count": 4}}
prediction = {"type": "binary", "probability_yes": 0.3}
cdf = [0.001 + 0.998 * i / 200 for i in range(201)]
valid = [(binary, prediction), (choice, {"type": "multiple_choice", "probability_yes_per_category":
         {"A": 0.2, "B": 0.3, "C": 0.5}}), (numeric, {"type": "numeric", "continuous_cdf": cdf}),
         (discrete, {"type": "discrete", "continuous_cdf": [0, 0.25, 0.5, 0.75, 1]})]
for q, p in valid:
    assert f.payload(q, p)["question"] == 12
for value in (True, "0.3", float("nan"), float("inf"), 0, 1, 2 ** 10000):
    fails(lambda: f.payload(binary, {**prediction, "probability_yes": value}))
fails(lambda: f.payload(binary, {**prediction, "extra": 1}))
fails(lambda: f.payload(choice, prediction))
for value in ({"A": 0.5, "B": 0.5}, {"A": 0.2, "B": 0.3, "C": 0.4},
              {"A": 0, "B": 0.5, "C": 0.5}):
    fails(lambda: f.payload(choice, {"type": "multiple_choice", "probability_yes_per_category": value}))
too_tall = [0.001] + [0.251 + 0.748 * i / 199 for i in range(200)]
for value in (cdf[:-1], [0] + cdf[1:], cdf[:-1] + [1], [0.5] * 201, too_tall,
              cdf[:100] + [0.1] + cdf[101:], cdf[:100] + [float("nan")] + cdf[101:]):
    fails(lambda: f.payload(numeric, {"type": "numeric", "continuous_cdf": value}))
for value in ([0.001, 0.25, 0.5, 0.75, 1], [0, 0.25, 0.5, 0.75, 0.999]):
    fails(lambda: f.payload(discrete, {"type": "discrete", "continuous_cdf": value}))
fails(lambda: f.latest_values({"type": "binary"}))


class Server:
    def __init__(self, root, failure=""):
        self.root, self.failure, self.actual, self.calls = root, failure, None, []

    def __call__(self, path, data=None):
        if data is None:
            q = {**binary, "title": "Synthetic question", "my_forecasts":
                 {"latest": {"forecast_values": self.actual}} if self.actual is not None else None}
            post = {"id": 10, "question": q}
            return {"results": [post]} if path.startswith("/posts/?") else post
        self.calls.append(path)
        state = f.read(self.root / "submissions/10.json")
        stage = "forecast" if path == "/questions/forecast/" else "comment"
        assert state[stage] == "pending"  # Persistence precedes each external send.
        if stage == "forecast" and self.failure != "forecast-before":
            self.actual = f.forecast_values(binary, data[0])
        if self.failure.startswith(stage):
            raise TimeoutError("synthetic lost response")
        if stage == "comment":
            assert data["on_post"] == 10 and data["is_private"] and data["included_forecast"]
        return {"id": 99}


temp_root = Path(sys.argv[1]).resolve()
temp_root.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="forecast-ledger-check-", dir=temp_root) as work:
    for failure in ("", "forecast-before", "forecast-after", "comment"):
        root = Path(work) / (failure or "success")
        server = Server(root, failure)
        f.api = server
        assert f.poll(root, ["synthetic"])[0]["question"] == 12
        send = lambda: f.submit(root, 10, copy.deepcopy(prediction), "Synthetic evidence. Probability: 30%.")
        if failure:
            fails(send)
        else:
            assert send()["comment"] == "sent"
        prior = len(server.calls)
        server.failure = ""
        if failure in ("forecast-before", "comment"):
            fails(send)
            assert len(server.calls) == prior
        else:
            assert send()["comment"] == "sent"
            assert server.calls == ["/questions/forecast/", "/comments/create/"]
            send()
            assert len(server.calls) == 2
            assert f.poll(root, ["synthetic"]) == []
            server.actual = [0.6, 0.4]
            fails(send)
            assert len(server.calls) == 2
print("PASS: four payload types, malformed inputs, poll, duplicate prevention, and interrupted sends")
