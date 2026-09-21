# Architecture analysis

One vendor module changes; no schema or dependency migration. New draft_* diagnostics are bounded to an allowlist and retain validated provider response digests. State remains needs_human with category draft, so draft rejection still does not trigger provider fallback. Preserve historical receipts and runtime state. Rollback restores the old module.
