# One-unit sub-agent fan-out contract

Use this whenever a stage needs many independent model judgments or retrievals.
Resolve the local working root under `storage.md` first; workers get that
directory and absolute assignment paths and never touch the project home.

- **Coding and audit** (Stage 11; Stages 08, 12, and 15 for pilots, audits, and
  robustness): one frozen unit per worker, prepared, checked, and closed by
  `scripts/coding_run.py` from a settings file
  (`workflow/templates/coding_run_settings.md`) and controlled by
  `scripts/unit_fanout.py`. Write settings, never a driver.
- **Research** (Stage 02 searches and retrieval, Stage 07 critics, Stage 19
  claim-citation pairs, add-citations retrieval, fresh reviews): one bounded
  task per worker, controlled by `scripts/research_fanout.py`.

## The host orchestrates; the kit validates

The host's orchestrator runs workers in a bounded rolling pool, never serial
work in the parent context and never an all-tools default agent: on Claude Code
the saved workflows `elr-observation-fanout` and `elr-research-fanout`, which the
assistant launches itself; on Codex the custom sub-agents `elr_worker` and
`elr_research_worker` (`.codex/agents/`), spawned by name. The controllers seal
the manifest, list what is pending, validate, bound attempts, and merge, so the
files are the same on either host and an interrupted fan-out resumes with the
same command. Without the orchestrator: on Claude Code (workflows disabled, or
older than 2.1.154) launch the same restricted types directly, one assignment
per call, and record the route; on Codex set `waiting_for_user` and ask the
researcher to enable sub-agents, or run the API route the pilot fixed.

## Launching, relaunching, and concurrency

An assignment is pending until its return exists; the launcher call (`status
--record-launch`) lists pending assignments and records one launch each.

- **The first valid return wins.** A coding return is created once by `submit`
  (a later one is `already_submitted`); for research, the lowest-numbered
  complete attempt not marked unusable is the result. A duplicate launch never
  changes a recorded result, and no outcome is chosen among.
- **One failed worker never stops the batch;** its assignment stays pending.
  A coding assignment launched twice without a return becomes a typed
  `worker_error` for the frozen retry rule; a research assignment moves to its
  next sealed attempt and is `exhausted` after `max_attempts`.
- **Concurrency** is fixed: six by default, `concurrency` otherwise (at most 16
  on Claude Code), lower when the host, researcher, instrument, or a provider
  requires, never chosen from labels or findings. Approved batches (`block`,
  `limit`), research rounds, retry rules, and cost ceilings bound each launch;
  run one launcher per run directory, never while its workers run.

## Freeze, isolate, and hand in

- Before launch, freeze and hash the unit list, instructions, schema, source
  representation, model and effort, retry policy, batch size, and cost ceiling,
  in an immutable manifest of attempts, each with a unique assignment ID, unit
  ID, input hashes, and one return path in the run directory that names no
  shared file. Drift stops the run. Switching between API and sub-agent routes
  changes the instrument.
- Each worker gets a fresh, non-forked context (`fork_turns: "none"` or the
  verified equivalent) and one assignment: the frozen instructions, schema, and
  that unit's authorized source, never earlier answers, counts, gold labels, or
  other workers' files, which it must not read; report the limit where the
  platform cannot enforce that.
- A coding or audit worker writes its envelope to
  `<run-dir>/drafts/<assignment-id>.json`, runs `python scripts/unit_fanout.py
  submit --run-dir <run-dir> --assignment-id <id> --input <draft-path>`, and
  reports only the controller's receipt. Workers never merge, edit ledgers,
  code, or state, retry, or drop a unit.

## Worker tool surface, time boxes, and crash-resume

1. **Restricted types only** (`.claude/agents/elr-worker.md` and
   `elr-research-worker.md`; `.codex/agents/elr-worker.toml` and
   `elr-research-worker.toml`): coding and audit workers have no web; research
   workers have web fetch and search and write only their return. Neither
   reaches the in-app browser, computer use, MCP tools, sub-agent spawning, or
   user prompts. A missing role follows "When something breaks".
2. **Access walls are typed gaps.** On a 401/403/429, CAPTCHA,
   human-verification page, or login wall a worker records `{url,
   status_or_message, timestamp_utc}` and moves on (one retry at most for a 429,
   no spoofing). Walled sites (`papers.ssrn.com`, HeinOnline, Westlaw, Lexis,
   JSTOR, Google Scholar) are reached only through open APIs and indexes or the
   researcher's own session.
3. **Time boxes:** about 12 minutes per research unit and 10 per coding unit;
   network calls time out after about 60 seconds. A worker far past its box is
   stopped from the host's run view and relaunched by the next launcher run.
4. **Crash-resume.** Manifests, assignments, returns, drafts, and launch records
   (`launches.jsonl`, `attempts.jsonl`) live under the run directory, never in a
   session scratchpad. Exhausted assignments go into the stage's limitations;
   more work starts a new versioned wave.
5. **Checkpoints.** The parent validates and merges serially with atomic
   writes, then appends a ledger checkpoint. Stage 11 unit failures are decided
   under `guardrails.md` §11 and logged in `failure_decisions.jsonl`.
   At validation checkpoints scan for unexpected writes, including the
   repository root; only returns, drafts, attempt files, and launch records are
   expected. Record each containment finding with its path and disposition and
   stop launching if it repeats. About every five minutes report terminal,
   active, and outstanding counts, elapsed time, retries, and an ETA range from
   observed completed-assignment throughput and the remaining work, including
   required batch drains. Never expose interim labels or outcome distributions.

## Research fan-outs

Each brief is frozen; the investigation is not. Version follow-up work, and
never rerun a judgment for a preferred answer or show reviewers each other's
findings. Write `spec.json` (`fanout_id`, `kind`,
`time_box_minutes`, `max_attempts`, `assignments`) and one `briefs/<id>.md` per
assignment, then run `python scripts/research_fanout.py prepare --fanout-dir
<dir>` to seal one manifest row per allowed attempt. A brief holds everything
one unit needs (the verbatim query and routes, or the work under review; the
result schema; the time box; the access-gap rules) and nothing it must not see.
Workers write `returns/<id>__attempt-NNN.json` with `assignment_id`, `attempt`,
`complete`, the `result` fields, and `access_gaps`; `status` reconciles
`attempted`, `succeeded`, `failed`, `unusable`, and `outstanding`. Never edit a
complete return that fails the stage's schema: run `research_fanout.py
record-disposition --terminal unusable --reason <failure>` and the next launch
offers the next attempt; `--include-exhausted` never reopens or reuses a return
path. Merge in assignment order from the returns `status --include-returns`
names.

## Parent-only browser fallback for Stage 02

Browser control is a serial step in the parent's session, never a worker tool.
For a material access gap after a Stage 02 wave, recheck lawful open routes
first. A host is **challenge-evidenced** when any fetch in the project met a 403,
CAPTCHA, or human-verification page there, or it is a walled or
Cloudflare-fronted host (the sites above, `academic.oup.com`). Never open such a
host in the host application's in-app browser pane, whose challenge page crashes
the desktop app faster than a tool call can close it; route it to the
researcher's separate browser session (such as the Chrome extension) or the
manual search packet. Any other host gets one bounded ordinary-UI attempt in
the researcher's main session (on Claude Code one batched sequence: navigate,
one text read, then a blank page), signed in only where the authorization
permits. Never inspect credentials or session stores, spoof a client, bypass a
CAPTCHA, evade a paywall or terms, or construct a download URL. Logins,
CAPTCHAs, licenses, and purchases stay with the researcher, and a challenge page
that appears anyway ends the attempt. Log each source in `search_log.csv` with
route `parent_browser_fallback`, and verify a download is the identified work
before hashing it into `retrieved/`.

## Codex adapter

The parent keeps the plan and any covering goal; do not create a narrower
fan-out goal. Get the batch with `python scripts/unit_fanout.py status --run-dir
<run-dir> --record-launch` (or `research_fanout.py status --fanout-dir <dir>
--record-launch`), with any approved `--limit` or `--block`, and spawn exactly
the listed `pending_assignments`, one fresh `elr_worker` or
`elr_research_worker` each, refilling slots as they finish, after confirming
the host lists those agents. A CSV batch tool may
run them only with the restricted agent or a sandbox confirmed for that turn to
have no network, MCP, or browser tools, recorded in the run manifest.

## Claude Code adapter

`elr-observation-fanout` takes `{ "run_dir": "<run-dir>" }` and
`elr-research-fanout` `{ "fanout_dir": "<dir>" }` (optional `block`, `limit`,
`concurrency`, `model`, `effort`). Workers never create goals or plans. One
invocation launches at most 998 workers; run it again for the rest within the
batch. It returns counts and `no_receipt`, the assignments still pending; one
null result is not a rate-limit diagnosis, and the `Large workflow` notice is
advisory. Record a set
`CLAUDE_CODE_SUBAGENT_MODEL` in the run manifest as capability drift.

## Serial validation and provenance

The parent validates IDs, schema, quotations, statuses, hashes, and path scope,
keeps invalid returns with a linked retry attempt, merges in manifest order once
all are terminal, and has a fresh reviewer (`fresh-review.md`) inspect the chain
from source to aggregate. Record the platform, route, model, effort (or
`unobservable`), host version, timestamps, concurrency, usage, and errors.
