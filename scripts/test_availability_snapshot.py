import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import availability_snapshot as snapshot


class CaptureTests(unittest.TestCase):
    def test_same_day_reads_preserve_raw_bytes(self):
        with TemporaryDirectory() as root:
            history = Path(root)
            time = datetime(2026, 11, 19, tzinfo=timezone.utc)
            payloads = (b'<tr>\xff\r\n', b'<tr>\x80\r\n')
            for index, payload in enumerate(payloads):
                self.assertEqual(snapshot.main(history, lambda url: (200, url, payload),
                                               lambda: time + timedelta(hours=index)), 0)
            with (history / 'manifest.csv').open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 4)
            reports = sorted(history.glob('reads/*/league-injury-report/response.bin'))
            self.assertEqual([p.read_bytes() for p in reports], list(payloads))
            for report in reports:
                meta = json.loads(report.with_name('meta.json').read_text())
                self.assertEqual(meta['sha256'], hashlib.sha256(report.read_bytes()).hexdigest())

    def test_wrong_report_destination_is_rejected_even_if_schedule_is_fresh(self):
        def fetch(url):
            return 200, ('https://www.nfl.com/' if 'injuries' in url else url), b'<tr>'
        with TemporaryDirectory() as root:
            history = Path(root)
            self.assertEqual(snapshot.main(history, fetch), 1)
            report = next(history.glob('reads/*/league-injury-report/meta.json'))
            self.assertFalse(report.with_name('response.bin').exists())
            self.assertIn('FRESHNESS ALERT', report.read_text())

    def test_empty_report_schema_is_flagged_but_evidence_is_retained(self):
        with TemporaryDirectory() as root:
            history = Path(root)
            self.assertEqual(snapshot.main(history, lambda url: (200, url, b'<html>')), 1)
            report = next(history.glob('reads/*/league-injury-report/meta.json'))
            self.assertEqual(report.with_name('response.bin').read_bytes(), b'<html>')
            self.assertIn('SCHEMA CHANGE ALERT', report.read_text())
