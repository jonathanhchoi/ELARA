# Fixture codebook

## Unit

One supplied constitutional clause.

## `has_shall`

- `true`: the supplied clause contains the exact token `shall` (case-insensitive).
- `false`: it does not.
- Do not infer obligation from synonyms.

## `assigned_institution`

- Record the institution named immediately after the phrase `vested in`.
- Allowed fixture values: `Congress`, `President`, `uncertain`.
- Use `uncertain` if the phrase or institution is absent.

Every non-uncertain code must include an exact quotation from the supplied clause. Return an
explicit non-`coded` status rather than a blank row if the source cannot be read.
