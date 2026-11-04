# Model access and research capacity

An advisory setup check, not a gate. The assistant inspects; the helper
`scripts/model_readiness.py` checks its secret-free evidence without network or
model calls. A passing software doctor is not proof of access to the best model.

## When

After installation, before substantive research in the first session; after a
kit update; when the researcher asks; and when the host, account, model route,
or permissions change. Do not repeat an unchanged warning at every stage.
Evidence older than 24 hours is rejected, and a new install or update needs new
evidence. `help`, `status`, and Plan Mode stay read-only: explain a pending
check there and save evidence only once writes are allowed.

## Collect evidence, not model guesses

1. Identify the platform doing the work (Codex or Claude Code) and its surface;
   another CLI's credentials prove nothing here.
2. From current official guidance ([Codex models](https://learn.chatgpt.com/docs/models),
   [Claude Code model configuration](https://code.claude.com/docs/en/model-config)),
   identify the provider's strongest generally available model for demanding
   research. Never rank by version numbers, list order, or memory; if guidance
   is ambiguous, leave it unresolved and say why.
3. Inspect account-scoped availability and the session's actual model and
   effort with the host's tools (`model/list` on Codex; `/model` and `/status`
   on Claude Code). Defaults, aliases, caches, generic catalogs, and settings do
   not prove entitlement, and a missing entry does not prove denial. Never make
   a paid test call.
4. Recommend the high-reasoning setting suited to research (Codex: Extra High or
   its equivalent) without escalating to special cost or speed modes; resolve
   aliases before comparing, and note worker model overrides.
5. From current plan terms ([OpenAI plans](https://learn.chatgpt.com/docs/pricing),
   [Claude Max plans](https://support.claude.com/en/articles/11049741-what-is-the-max-plan)),
   strongly recommend ChatGPT Pro 20x or Claude Max 20x (or the current
   highest-volume equivalent) for large-scale research, as guidance, not an
   eligibility test. Never buy, upgrade, switch accounts, change settings, or
   send research data as part of this check.

## Record and report

Fill the scaffold from `python scripts/model_readiness.py --platform
<codex|claude> --template` and save it as a new
`project/model_readiness_evidence_vNNN.json`. `effort_policy` is `resolved`,
`not_supported` (with evidence), or `unknown`; `sources` holds up to eight
`url`/`retrieved_at`/`finding` entries; `selection_kind` and `access.kind` may
be `active_session` only from native session evidence (`access.kind` also
`account_model_catalog` or `host_access_status`); `access.status` is
`unavailable` only with positive evidence of denial. No account identifiers,
credentials, or raw dumps. Run `python scripts/doctor.py --json --platform
<platform> --model-evidence <file>`, keep its `capability_record` in a new
`project/ACCESS_MODEL_SNAPSHOT_vNNN.md` with the evidence hash and plan sources,
and record it in the access-snapshot entry of `active_artifacts`; on an
initialized project these are the only writes this check authorizes.

Tell the researcher in chat: available and selected; available but not selected
(recommend switching, not buying); unavailable (warn prominently); or
unverified (say access could not be verified, not that it is missing). Include
the plan recommendation. Never change a frozen/preregistered model, its
settings, worker overrides, or an ongoing run to chase a newer model.
