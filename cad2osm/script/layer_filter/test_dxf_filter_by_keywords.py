import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = MODULE_DIR / "cad_layers_to_keep.json"
MODULE_PATH = MODULE_DIR / "dxf_filter_by_keywords.py"

# Configuration helpers do not use ezdxf, so a stub keeps this unit test
# independent from the optional CAD runtime dependency.
sys.modules.setdefault("ezdxf", types.ModuleType("ezdxf"))
spec = importlib.util.spec_from_file_location("dxf_filter_by_keywords", MODULE_PATH)
layer_filter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layer_filter)


class LayerFilterConfigTest(unittest.TestCase):
    def test_ncs_prefixes_and_nonstandard_aliases_are_separate(self):
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

        self.assertEqual(config["NCS"]["prefixes"], ["A-WALL"])
        self.assertNotIn("A-STAIR", json.dumps(config["NCS"]))
        self.assertIn("A-STAIR", config["common"]["aliases"])

    def test_ncs_wall_prefix_and_common_aliases_are_kept(self):
        params = layer_filter.load_filter_config(CONFIG_PATH, "NCS")

        self.assertTrue(layer_filter.should_keep_layer("A-WALL", params))
        self.assertTrue(layer_filter.should_keep_layer("a-wall-full", params))
        self.assertTrue(layer_filter.should_keep_layer("A-STAIR", params))
        self.assertFalse(layer_filter.should_keep_layer("A-WALLPAPER", params))
        self.assertFalse(layer_filter.should_keep_layer("A-ROOF", params))

    def test_reference_layers_are_always_kept(self):
        params = layer_filter.load_filter_config(CONFIG_PATH, "GB/T")

        self.assertTrue(layer_filter.should_keep_layer("0", params))
        self.assertTrue(layer_filter.should_keep_layer("defpoints", params))


if __name__ == "__main__":
    unittest.main()
