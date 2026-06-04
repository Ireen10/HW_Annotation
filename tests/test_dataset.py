"""Tests for HwAnnotationDataset and lean sample parsing."""

from __future__ import annotations

import unittest
from pathlib import Path

from hw_annotation import HwAnnotationDataset, parse_sample
from hw_annotation.io import iter_raw_records

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "samples.jsonl"


class TestHwAnnotationDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SAMPLES.is_file():
            raise unittest.SkipTest(f"missing {SAMPLES}")

    def test_length_and_scenario(self) -> None:
        ds = HwAnnotationDataset(SAMPLES)
        self.assertEqual(len(ds), 5)
        sample = ds[0]
        self.assertTrue(sample.scenario)
        self.assertEqual(sample.object_count, len(sample.objects))

    def test_strips_redundant_fields(self) -> None:
        raw = next(iter(iter_raw_records(SAMPLES)))
        d = parse_sample(raw).to_dict()
        self.assertNotIn("guidelines_text", d)
        self.assertNotIn("text", d)
        self.assertNotIn("_annot_worker", d)
        obj = d["objects"][0]
        self.assertNotIn("points", obj)
        self.assertNotIn("color", obj)
        self.assertIn("label", obj)
        self.assertEqual(len(obj["bbox_xyxy"]), 4)

    def test_guidelines_loaded_once(self) -> None:
        ds = HwAnnotationDataset(SAMPLES)
        g = ds.guidelines_text
        self.assertIsNotNone(g)
        self.assertGreater(len(g or ""), 100)
        sample_dict = ds[0].to_dict()
        self.assertNotIn("text", sample_dict)

    def test_relations_preserved(self) -> None:
        ds = HwAnnotationDataset(SAMPLES)
        total_rels = sum(s.relation_count for s in ds)
        self.assertGreater(total_rels, 0)
        has_topology = any(
            r.relationship_type == "topology"
            for s in ds
            for o in s.objects
            for r in o.relations
        )
        self.assertTrue(has_topology)


if __name__ == "__main__":
    unittest.main()
