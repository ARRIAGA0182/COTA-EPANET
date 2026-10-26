"""Unit tests for INP parsing and preservation; no drone raster required."""
import tempfile
import unittest
from pathlib import Path
from epanet_elevations import load_inp, patch

SAMPLE = """[TITLE]
Example network
[JUNCTIONS]
;ID Elev Demand Pattern
 N-01    0.0    0.50 ; existing comment
 N-02  120  0.10
[RESERVOIRS]
 R-1 250
[TANKS]
 T-1 220 5 0 10 8
[COORDINATES]
 N-01 500000 1700000
 N-02 500040 1700050
[END]
"""

class InpTests(unittest.TestCase):
    def test_only_junction_elevation_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "network.inp"
            inp.write_text(SAMPLE, encoding="utf-8")
            lines, coords, nodes = load_inp(inp)
            self.assertEqual(len(nodes), 2)
            self.assertEqual(coords["N-01"], (500000.0,1700000.0))
            ix = nodes["N-01"][0]
            changed = "".join(patch(lines, {ix:("N-01", "185.420")}))
            self.assertIn("N-01    185.420    0.50 ; existing comment", changed)
            self.assertIn("N-02  120  0.10", changed)
            self.assertIn("T-1 220 5 0 10 8", changed)
            self.assertIn("R-1 250", changed)
            self.assertIn("[END]", changed)

if __name__ == "__main__":
    unittest.main()
