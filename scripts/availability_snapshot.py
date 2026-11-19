#!/usr/bin/env python3
"""Archive official NFL responses byte-for-byte, with one immutable path per read.

New evidence lives under history/reads/<UTC timestamp>/<source>.html. Legacy
date-only evidence is left untouched; its original manifest remains readable.
A fetch timestamp is an observation time, not the report's publication time.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HIST = Path(__file__).resolve().parent.parent / 'readiness/data/history'
TARGETS = [
    ('league-injury-report', 'https://www.nfl.com/injuries/'),
    ('league-schedule', 'https://www.nfl.com/schedules/'),
]
MAX_AGE_DAYS = 4.0
SCHEMA_DELTA = 0.20
FIELDS = 'captured_at_utc slug url http_status bytes sha256 row_count'.split()


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X3 research snapshot)'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.getcode(), response.geturl(), response.read()


def main(history=HIST, fetch_page=fetch, clock=lambda: datetime.now(timezone.utc)):
    manifest = history / 'manifest.csv'
    previous = {}
    if manifest.exists():
        with manifest.open(newline='') as stream:
            for row in csv.DictReader(stream):
                if row['http_status'] == '200':
                    slug = row['slug']
                    if slug not in previous or row['captured_at_utc'] > previous[slug]['captured_at_utc']:
                        previous[slug] = row
    alerts = []
    for slug, url in TARGETS:
        effective_url, status, body = None, '000', None
        source_alerts = []
        try:
            status, effective_url, body = fetch_page(url)
            final = urlsplit(effective_url)
            expected = urlsplit(url)
            if (status != 200 or final.scheme != 'https' or final.hostname != expected.hostname
                    or not (final.path.rstrip('/') == expected.path.rstrip('/')
                            or final.path.startswith(expected.path)) or not body):
                raise ValueError(f'unexpected HTTP response: {status} {effective_url}')
        except Exception as exc:
            status, body = '000', None
            source_alerts.append(f'CAPTURE FAILED: {slug}: {exc}')
        observed = clock()
        timestamp = observed.isoformat(timespec='microseconds')
        key = observed.strftime('%Y%m%dT%H%M%S%fZ')
        folder = history / 'reads' / key / slug
        folder.mkdir(parents=True, exist_ok=False)
        count = 0
        digest = ''
        if body is not None:
            (folder / 'response.bin').write_bytes(body)
            digest = hashlib.sha256(body).hexdigest()
            count = len(re.findall(rb'<tr\b[^>]*>', body, re.I))
            prior_count = int(previous.get(slug, {}).get('row_count', 0))
            if slug == 'league-injury-report' and not count:
                source_alerts.append(f'SCHEMA CHANGE ALERT: {slug}: no table rows')
            elif prior_count and abs(count - prior_count) / prior_count > SCHEMA_DELTA:
                source_alerts.append(f'SCHEMA CHANGE ALERT: {slug}: {prior_count} -> {count} table rows')
        else:
            prior = previous.get(slug)
            if prior is None or (observed - datetime.fromisoformat(prior['captured_at_utc'])).total_seconds() / 86400 > MAX_AGE_DAYS:
                source_alerts.append(f'FRESHNESS ALERT: {slug}: no successful read within {MAX_AGE_DAYS:g} days')
        row = dict(zip(FIELDS, (timestamp, slug, url, status, len(body or b''), digest, count)))
        (folder / 'meta.json').write_text(json.dumps({**row, 'effective_url': effective_url, 'alerts': source_alerts}, indent=2) + '\n', encoding='utf-8')
        new_file = not manifest.exists()
        with manifest.open('a', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        print(f'{slug}: {timestamp}, HTTP {status}, {row["bytes"]} bytes')
        alerts.extend(source_alerts)
    for alert in alerts:
        print(f'::error::{alert}')
    return int(bool(alerts))


if __name__ == '__main__':
    raise SystemExit(main())
