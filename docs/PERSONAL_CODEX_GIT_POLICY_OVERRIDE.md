# Repository Git Policy

Use precise staging and preserve unrelated user changes. Runtime databases, installed capabilities, user choices, audit receipts, caches and generated personal projections remain local.

Local commits are allowed when requested by the active task. Remote push and release creation require explicit task-scoped authorization. After a release, automatic push returns to **NO_BY_DEFAULT**. Never force push, rewrite public history or move an existing release tag without separate authorization.

Public contact is separate from Git author identity. Prefer a verified GitHub noreply author address; do not infer an author address from the public contact mailbox.
