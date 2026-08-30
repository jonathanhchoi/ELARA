# Model access and research capacity

This is an advisory setup check, not a research gate. The installing assistant
does the live inspection; `scripts/model_readiness.py` checks and reports its
secret-free evidence without network or model calls. A successful software
doctor is not proof of access to the best model.

## When to check

- Complete this check after installation, before substantive research in the
  first session (both the fresh and adoption paths, including specific tools).
- Repeat after a kit update, when the researcher asks, or when the host,
  account, model route, or relevant permissions change. An update does not
  reinitialize the project or authorize a model change.
- A standalone installer cannot inspect an interactive session. It warns that
  verification is pending and hands this check to the assistant at first use.
- Do not repeat an unchanged warning on every stage. Keep its date and result
  in the access snapshot. A new install/update needs new evidence even if an
  earlier record is less than 24 hours old. The helper rejects evidence older
  than 24 hours; this is a maximum freshness bound, not a guarantee of access.
- `help`, `status`, and read-only Plan Mode remain read-only. Explain a pending
  check there, and save evidence only when setup/execution writes are allowed.

## Collect evidence, not model guesses

1. Identify the platform actually doing the work: Codex or Claude Code. Check
   only that provider unless both routes are planned. Record the actual host
   surface (desktop, CLI, or other supported integration). A different CLI's
   credentials or configuration do not prove access in the active desktop app.
2. Retrieve current **official** model guidance for that platform. Start with
   [Codex models](https://learn.chatgpt.com/docs/models) or
   [Claude Code model configuration](https://code.claude.com/docs/en/model-config).
   Follow current official pages when these move. Identify the provider's
   strongest generally available model for demanding reasoning/research work,
   independently of what this account can use. Do not substitute the newest
   small/fast model, the account default, a preview restricted to special
   partners, or a model available only on a different product. Never rank model
   names by version numbers, list order, or a hard-coded family hierarchy.
   Record the resolved model ID, source URLs, retrieval times, and short
   evidence summaries. If current guidance is unavailable or ambiguous, leave
   the recommendation unresolved and disclose why; do not use model memory.
3. Inspect native, account-scoped model availability and the actual session's
   model/effort using the host's exposed tools or supported status/model UI.
   For Codex, an available `model/list` interface supplies models and supported
   reasoning efforts; inspect pagination and scope. `isDefault`, `upgrade`,
   hidden entries, a local cache, or a generic catalog alone do not prove this
   account can use the strongest model. See the
   [app-server reference](https://learn.chatgpt.com/docs/app-server#list-models-modellist).
   For Claude Code, inspect `/model` availability and `/status`; a `best` or
   family alias can resolve to a fallback or be remapped. Resolve the actual
   model, organization restrictions, disabled entries, and credit notices.
   Neither a successful CLI version check nor a model string in settings is
   proof of entitlement. A missing catalog entry alone does not prove denial.
   Do not start a paid test request or a new model session to verify access.
   If the host cannot expose the needed evidence, ask once for the relevant
   model/status information if useful; otherwise report unknown and continue.
4. Check the **selected** configuration separately from access. Recommend the
   high-reasoning configuration suited to demanding research, using current
   official guidance and the host's supported settings. In Codex, prefer Extra
   High when supported or its documented equivalent. Do not automatically
   escalate to Max, Ultra, Pro reasoning mode, or other special cost/speed
   modes. Do not assume equal effort names are equivalent across providers.
   Record the recommended and actual effort identifiers; if effort is not
   supported, record that explicitly with source support. Resolve aliases
   before comparing model IDs; do not label an unresolved alias a confirmed
   match or mismatch. Also disclose worker overrides if they differ from the
   parent's model: access in the parent does not certify every worker's route.
5. Retrieve the current applicable plan terms: [OpenAI
   plans](https://learn.chatgpt.com/docs/pricing) or [Claude Max
   plans](https://support.claude.com/en/articles/11049741-what-is-the-max-plan).
   Strongly recommend **ChatGPT Pro 20x** or **Claude Max 20x**, respectively,
   for large-scale research, or their current highest-volume equivalents.
   These named plans are reference recommendations, not eligibility tests.
   Record dated plan findings in the snapshot; if terms cannot be refreshed,
   identify the plan names as unverified reference guidance. Never infer the
   exact plan multiplier from a generic `pro`/`max` account label. Adequate
   institutional access need not be replaced with a personal subscription.
   Higher capacity is not unlimited usage or a guarantee that every model is
   included. Explain any model-specific credit requirement and distinguish
   subscription access from separately billed API usage. Never buy credits,
   upgrade a subscription, relax an organization policy, switch accounts,
   change settings, or send research data as part of this check.

## Evidence and reporting

The assistant runs all commands; never ask the researcher to edit JSON.
Generate a scaffold with:

```text
python scripts/model_readiness.py --platform codex --template
```

Use `claude` instead on Claude Code, and `all` only if both routes are in scope.
Fill the scaffold from the observations above. Its exact contract is:

- Top level: `schema_version: "1.0"` and `platforms`, mapping `codex` and/or
  `claude` to records. An omitted platform is unverified, not available.
- Each record: `checked_at` (timezone-aware ISO timestamp), `host_surface`,
  `recommended_model`, `recommended_effort`, `effort_policy`, `sources`,
  `current_model`, `current_effort`, `selection_kind`, and `access`. Use null for
  unknown IDs. `selection_kind` is `active_session` only when native session
  evidence establishes the running configuration; `configuration`,
  `user_report`, and `unknown` cannot establish a verified selection. A settings
  file alone is not evidence of the configuration an existing session uses.
- `effort_policy`: `resolved` when `recommended_effort` is supplied,
  `not_supported` only with evidence that this model has no effort setting,
  otherwise `unknown` with a null recommended effort.
- `sources`: up to eight objects with `url`, `retrieved_at`, and `finding`.
  Use canonical HTTPS provider URLs without query strings or credentials and
  concise paraphrases, not whole pages. Include model and effort evidence.
- `access`: `status` (`available`, `unavailable`, or `unknown`), `kind`,
  `model` (the exact model the observation concerns), `observed_at`, and
  `detail` (a short account/surface-scoped evidence summary with no account ID).
  `kind` is `active_session` for the actual running model,
  `account_model_catalog` for an explicitly account-scoped available-model
  list, or `host_access_status` for a direct access/denial status. Use
  `catalog_only` for generic/cached catalogs, `configuration` for settings,
  `user_report` for the researcher's report, or `unknown` when not inspected.
  These last four cannot establish verified availability or denial. Use
  `unavailable` only for positive evidence of denial/restriction, not an absent
  entry, timeout, login failure, or lack of browsing.

Store the evidence as a new `project/model_readiness_evidence_vNNN.json` file,
never overwrite one. Do not read or copy credential files. Include only the
listed fields; omit emails, account identifiers, tokens, keys, and raw host
dumps. The helper checks structure, freshness, and source domains; it cannot
authenticate an assertion or prove that the assistant fetched a source.

```text
python scripts/doctor.py --json --platform codex --model-evidence project/model_readiness_evidence_vNNN.json
```

Preserve the resulting `capability_record` in the new
`project/ACCESS_MODEL_SNAPSHOT_vNNN.md`, together with the evidence path/hash,
the plan sources/date, restrictions, failed checks, and whether facts were
verified or researcher-reported. Record the new snapshot in the existing
access-snapshot entry in `active_artifacts`; do not change unrelated state or
invalidate approvals merely because the check ran. On an already initialized
project, these two versioned setup files and that snapshot reference are the
only additional writes this check authorizes, alongside the existing decision
record if the researcher makes a choice. Never mutate the approved instrument.
For a just-installed project, combine this with Stage 00's snapshot instead
of creating a duplicate. An installer may also receive `--model-evidence` when
fresh evidence has already been collected for the active host.

Tell the researcher the result in chat; do not bury it in the doctor's JSON:

- **Available and selected:** identify the model and reasoning setting.
- **Available but a different selection:** strongly recommend selecting the
  recommended model/effort; do not recommend buying an upgrade just to switch.
- **Unavailable:** prominently warn and strongly recommend upgrading the plan
  or obtaining the needed access before substantial research. Explain whether
  an app update, organization permission, or credits are the actual issue.
- **Unverified:** prominently say access could not be verified, not that it is
  missing. Strongly recommend checking it and upgrading if needed. State what
  was attempted and what remains unknown.

Include the applicable high-volume plan recommendation in the setup summary,
even when model access is confirmed. Installation may finish in every case.
No acknowledgment or upgrade is a new gate; respect the researcher's choice
to continue, existing budgets, data restrictions, and all existing gates.
Never change a frozen/preregistered model, its reasoning settings, worker
overrides, or an ongoing run to chase a newer model. Propose any such change
through the existing decision, versioning, and revalidation process.
