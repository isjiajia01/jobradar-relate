"""Metric arithmetic on toy IDs, independent of either Djinni sample."""
from fractions import Fraction
import unittest
from jobradar_relate.holdout_eval import metrics, validate_labels


class HoldoutMetricsTests(unittest.TestCase):
    def test_cutoff_tie_includes_neutrals(self):
        scores = dict(a=2, b=1, c=1, d=1)
        labels = dict(a='LIKED', b='DISMISSED', c='NEUTRAL', d='LIKED')
        self.assertEqual(metrics(scores, labels), (Fraction(3, 2), 2, Fraction(4, 3)))

    def test_one_class(self):
        self.assertEqual(metrics({'a': 1}, {'a': 'DISMISSED'}), (0, 0, 0))

    def test_malformed_labels(self):
        jobs = [{'id': str(i)} for i in range(50)]
        records = [dict(job, label='NEUTRAL') for job in jobs]
        self.assertEqual(len(validate_labels(records, jobs)), 50)
        for rows in (records[:-1], records + [records[0]],
                     records[:-1] + [dict(id='other', label='LIKED')],
                     records[:-1] + [dict(id='49', label='invalid')]):
            with self.assertRaises(ValueError):
                validate_labels(rows, jobs)
