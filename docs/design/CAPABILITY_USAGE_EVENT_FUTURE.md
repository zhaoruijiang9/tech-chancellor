# Future Capability Usage Event

This is design-only for a later product decision. MVP v1.2 does not create a
table, API, automatic collector, feedback mutation, or real Codex usage event.

Possible future events are `CONSIDERED`, `USED_AS_REFERENCE`, `PATTERN_APPLIED`,
`REJECTED_FOR_CURRENT_TASK`, and `SOLVED_PROBLEM`. Any implementation must keep
SQLite authoritative, preserve the distinction between reviewed/tested/used,
and require evidence or explicit user confirmation for `USED`.
