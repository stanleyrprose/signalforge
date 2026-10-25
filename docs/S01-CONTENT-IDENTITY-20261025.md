# S01 article identity and content versions — 2026-10-25

Status: merged in PR #325 at `1578631af25527446f8e7e4afecae34e64a517b9` and deployed to Mac and Bangkok on 2026-10-25. Full unittest suite: 539 PASS; PR and main CI passed. A real two-fetch probe confirmed changed raw HTML SHA with byte-identical extracted article text. Receipt-confirmed legacy metadata was reconciled for 202 articles on each host with database backups retained. The first post-deployment daily processing remains independently tracked in the takeover audit.

A real repeated fetch returned different raw HTML SHA values for identical extracted article text. Raw HTML SHA is evidence identity and must be retained; it is insufficient to classify a news article as materially updated.

- Article identity uses the official Liferay asset entry ID, including the same-host nested redirect query emitted by the real portal. Pagination/redirect locator changes do not create a new article. Conflicting asset IDs fail closed.
- Content identity is SHA-256 of NFC-normalized extracted article text with whitespace collapsed. Changed words, numbers and punctuation remain material. Raw acquisition SHA remains separately stored.
- Mac preparation and Bangkok sender independently exclude receipt-confirmed unchanged content. Existing PDF/Digest receipt identities remain intact. A real changed body remains eligible.
- The merged baseline retained both content fingerprints and validated AI reviews for reuse. Under the newer [cleanup amendment](NEWS-PROCESSING-POLICY-20261025.md), post-success cleanup removes retained AI text and keeps only minimum fingerprints/receipts. Exact-body dedup remains; translation reuse is available only while a permitted cached review still exists. Do not promise permanent translation caching after cleanup.
- Existing ledger rows are not deleted or renumbered. Legacy URL identities are reconciled through their retained official URLs. Backfill content metadata only when the retained review DB raw SHA exactly matches the receipt-confirmed delivered SHA. Unresolved revisions do not qualify as delivered.
- Earlier prepared manifests are immutable. Reconcile them against confirmed receipts before archiving or regenerating; never send them merely because their raw HTML SHA differs.

Current product authority remains [the news delivery contract](S01-S52-S53-NEWS-DELIVERY-CONTRACT.md). This change is confined to the independent S01 news ledgers; Tender Core canonical state and source registry are outside its scope.
