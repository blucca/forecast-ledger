# Forecast Ledger

**One forecast. Its sources. A durable receipt.**

A small, dependency-free Python adapter for an autonomous forecasting agent on [Metaculus](https://www.metaculus.com/futureeval/). It fetches open questions, checks probability distributions, and publishes a forecast with its private explanation. Local receipts let the agent resume interrupted publication.

The research agent supplies the estimate and a concise evidence summary. [FORECASTER.md](FORECASTER.md) describes the research protocol.

## Current stage

Protocol pilot, 15 October 2026. The local check covers all four supported forecast types and interrupted publication. Four real questions from the official testing area also pass offline field validation. Authenticated end-to-end publication is the next milestone after the operator creates the primary bot account.

## Run

Python 3.10+ on Linux or macOS. State lives in a private directory outside this repository. Set `METACULUS_TOKEN` to the **bot account's** API token.

```sh
python -B forecast.py --state "$PRIVATE_FORECAST_STATE" poll bot-testing-area
python -B forecast.py --state "$PRIVATE_FORECAST_STATE" show POST_ID
python -B forecast.py --state "$PRIVATE_FORECAST_STATE" submit POST_ID prediction.json explanation.md
```

Use the **post ID** from the question URL in these commands. The adapter reads the distinct question ID from the API response.

After testing, the seasonal and MiniBench queues can be read together:

```sh
python -B forecast.py --state "$PRIVATE_FORECAST_STATE" poll fall-futureeval-2026 minibench
```

Polling returns fresh research tasks and unfinished receipts. Published forecasts are omitted. A host scheduler invokes the adapter; the agent uses the returned deadline to organize its work.

### Prediction input

Binary:

```json
{"type":"binary","probability_yes":0.3}
```

Multiple choice, using the question's exact option labels:

```json
{"type":"multiple_choice","probability_yes_per_category":{"A":0.2,"B":0.3,"C":0.5}}
```

Numeric or discrete:

```json
{"type":"discrete","continuous_cdf":[0,0.25,0.5,0.75,1]}
```

The discrete example applies to a four-bin, closed-bound question. Numeric questions normally require 201 CDF values; discrete questions use the API's `inbound_outcome_count + 1`. Values follow the question's `scaling.continuous_range`. The adapter validates probability sums, finite values, monotonic increments, open/closed boundaries, and the API's per-bin probability limits.

### Explanations and receipts

`explanation.md` contains the evidence timestamp, final probability or quantiles, a short justification, and source URLs. Comments are submitted as private notes; FutureEval publishes them under its tournament policy.

Both outgoing requests are recorded before transmission. A later run matches the recorded forecast against `my_forecasts.latest.forecast_values` before continuing. A lost comment receipt remains pending for an agent to inspect through the comments API. Resumption uses the original prediction and explanation files.

The ledger stores raw question snapshots, probability payloads, explanations, and API receipts. The access token remains in the environment. One process holds the state-directory lock during each command.

## Check

Pass a temporary directory in your workspace:

```sh
python -B check.py /path/to/workspace/temp
```

The check uses an in-process synthetic server. It exercises four payload types, malformed values, completed-task filtering, duplicate protection, and lost responses before and after a forecast is accepted.

## Forward-practice examples

- [EU notification, binary](examples/eu-notification.md): the title discusses leaving the EU; the resolution counts an Article 50 **notification**. The stored estimate is 0.5%, dated 15 October 2026. This is an offline testing-area exercise.
- [BTC close, numeric](examples/btc-close.md): a current price, complete daily candles, a three-day volatility model, and an API-shaped CDF. The original competition window had closed, so this is an offline forward exercise.

These examples have zero scored tournament submissions. Their values preserve their original evidence timestamps.

## API references

- [Official participation resources and rules](https://www.metaculus.com/notebooks/38928/bot-tournament-resources-page/)
- [API documentation](https://www.metaculus.com/api/)
- [Official reference bot](https://github.com/Metaculus/metac-bot-template)
- [Current API validators](https://github.com/Metaculus/metaculus/blob/main/questions/serializers/common.py)

Forecast Ledger contains original adapter code under the MIT license. Account creation and identity verification belong to the human operator; the agent performs research and API publication.
