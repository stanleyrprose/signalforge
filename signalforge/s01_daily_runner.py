"""Mac-only S01 daily orchestration. Publishing requires explicit opt-in.

Separate from Tender Core and its scheduler. A failed coverage gate never sends.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .s01_news_review import acquire_paginated_news_review, acquire_news_details
from .s01_codex_review_runner import run as review
from .s01_daily_prepare import prepare
from .s01_daily_transfer import transfer


@contextmanager
def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run(root: Path, *, day: str, max_pages: int = 20, batch_size: int = 4,
        font: Path = Path('/System/Library/Fonts/Hiragino Sans GB.ttc'),
        publish: bool = False, host: str = 'vps-bangkok',
        remote_inbox: str = '/srv/signalforge/state/s01-news-inbox',
        remote_ledger: str = '/srv/signalforge/state/s01-news-ledger.sqlite',
        remote_python: str = '/srv/signalforge/active/.venv/bin/python') -> dict:
    if not 1 <= max_pages <= 20:
        raise ValueError('max_pages must be 1..20')
    root = root.resolve()
    with _lock(root / '.runner.lock'):
        evidence = root / 'evidence' / day
        output = root / 'outbox'
        db = evidence / 's01-news-review.sqlite'
        ledger = root / 's01-delivery.sqlite'
        evidence.mkdir(parents=True, exist_ok=True)
        pagination = acquire_paginated_news_review(db, evidence, max_pages=max_pages)
        if pagination['pagination_incomplete'] or not pagination['unique_candidates']:
            raise RuntimeError('S01 pagination incomplete/empty; no publication')
        details = acquire_news_details(db, evidence, limit=pagination['unique_candidates'])
        # Individual detail failures remain visible in the audit; publish successful articles.
        result = review(db, evidence, batch_size=batch_size)
        if result['excluded'] or result['included'] < 1 or result['included'] + result['unresolved'] != pagination['unique_candidates']:
            raise RuntimeError('S01 AI/coverage accounting invalid; no publication')
        prepared = prepare(evidence / 'coverage-audit.json', ledger, output,
                           day=day, fontfile=font)
        if prepared['status'] == 'NO_NEW_ARTICLES':
            return prepared
        if not publish:
            return {'status': 'READY_NOT_PUBLISHED', 'edition_id': prepared['edition_id'],
                    'articles': result['included'], 'manifest': prepared['manifest']}
        sent = transfer(Path(prepared['manifest']), ledger, output, host=host,
                        remote_inbox=remote_inbox, remote_ledger=remote_ledger,
                        python=remote_python)
        return {'status': 'DELIVERED', **sent}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--date', default=datetime.now(ZoneInfo('Asia/Yangon')).date().isoformat())
    parser.add_argument('--max-pages', type=int, default=20)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/Hiragino Sans GB.ttc'))
    parser.add_argument('--publish', action='store_true', help='Send via Bangkok after complete audit')
    parser.add_argument('--host', default='vps-bangkok')
    parser.add_argument('--remote-inbox', default='/srv/signalforge/state/s01-news-inbox')
    parser.add_argument('--remote-ledger', default='/srv/signalforge/state/s01-news-ledger.sqlite')
    parser.add_argument('--remote-python', default='/srv/signalforge/active/.venv/bin/python')
    args = parser.parse_args()
    print(json.dumps(run(args.root, day=args.date, max_pages=args.max_pages,
                         batch_size=args.batch_size, font=args.font, publish=args.publish,
                         host=args.host, remote_inbox=args.remote_inbox,
                         remote_ledger=args.remote_ledger,
                         remote_python=args.remote_python), ensure_ascii=False))


if __name__ == '__main__':
    main()
