# S01 article identity and content versions — 2026-10-25

Status: implemented and verified in development; release/deployment pending. Full unittest suite: 539 PASS. A real two-fetch probe confirmed changed raw HTML SHA with byte-identical extracted article text.

A real repeated fetch returned different raw HTML SHA values for identical extracted article text. Raw HTML SHA is evidence identity and must be retained; it is insufficient to classify a news article as materially updated.

- Article identity uses the official Liferay asset entry ID, including the same-host nested redirect query emitted by the real portal. Pagination/redirect locator changes do not create a new article. Conflicting asset IDs fail closed.
- Content identity is SHA-256 of NFC-normalized extracted article text with whitespace collapsed. Changed words, numbers and punctuation remain material. Raw acquisition SHA remains separately stored.
- Mac preparation and Bangkok sender independently exclude receipt-confirmed unchanged content. Existing PDF/Digest receipt identities remain intact. A real changed body remains eligible.
- Successful receipt metadata retains the content fingerprint and validated AI review. Identical source text can reuse receipt-confirmed translation; a different body must be reviewed again.
- Existing ledger rows are not deleted or renumbered. Legacy URL identities are reconciled through their retained official URLs. Backfill content metadata only when the retained review DB raw SHA exactly matches the receipt-confirmed delivered SHA. Unresolved revisions do not qualify as delivered.
- Earlier prepared manifests are immutable. Reconcile them against confirmed receipts before archiving or regenerating; never send them merely because their raw HTML SHA differs.

Current product authority remains [the news delivery contract](S01-S52-S53-NEWS-DELIVERY-CONTRACT.md). This change is confined to the independent S01 news ledgers; Tender Core canonical state and source registry are outside its scope.
