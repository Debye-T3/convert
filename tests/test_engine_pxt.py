import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from converter import engine
from converter.readers import igor_reader


def _reader_result(value: float = 1.0):
    return {
        "spectrum": np.array([[value, value + 1]], dtype=np.float32),
        "energy": np.array([10.0], dtype=np.float32),
        "thetax": np.array([-1.0, 1.0], dtype=np.float32),
        "ses_params": {},
    }


class PxtReaderSelectionTests(unittest.TestCase):
    def test_pxt_prefers_same_stem_txt_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pxt = root / "scan.pxt"
            txt = root / "scan.txt"
            pxt.write_bytes(b"placeholder")
            txt.write_text("placeholder")

            def fail_if_igor_is_used(*args, **kwargs):
                raise AssertionError(
                    "PXT conversion must not use the IGOR reader when TXT exists"
                )

            with (
                mock.patch.object(igor_reader, "load_experiment", fail_if_igor_is_used),
                mock.patch.object(engine, "read_txt", lambda path: _reader_result(7.0)),
            ):
                data = engine.read_as_xarray(pxt)

            self.assertEqual(data.name, "scan")
            self.assertEqual(data.dims, ("eV", "alpha"))
            np.testing.assert_array_equal(
                data.values, np.array([[7.0, 8.0]], dtype=np.float32)
            )
            self.assertEqual(data.attrs["source_reader"], "txt_sidecar")

    def test_pxt_without_txt_uses_da30_pxt_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pxt = root / "scan.pxt"
            pxt.write_bytes(b"placeholder")

            def fail_if_igor_is_used(*args, **kwargs):
                raise AssertionError("PXT conversion must use the DA30 PXT reader before IGOR")

            with (
                mock.patch.object(igor_reader, "load_experiment", fail_if_igor_is_used),
                mock.patch.object(
                    engine, "read_pxt", lambda path, **kwargs: _reader_result(3.0)
                ),
            ):
                data = engine.read_as_xarray(pxt)

            self.assertEqual(data.name, "scan")
            np.testing.assert_array_equal(
                data.values, np.array([[3.0, 4.0]], dtype=np.float32)
            )
            self.assertEqual(data.attrs["source_reader"], "da30_pxt")


if __name__ == "__main__":
    unittest.main()
