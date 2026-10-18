"""Run: python3 -m unittest -v test_diskclean   (uses a throwaway fake HOME)"""
import os
import sys
import tempfile
import unittest

FAKE_HOME = os.path.realpath(tempfile.mkdtemp(prefix="dc-home-"))
os.environ["HOME"] = FAKE_HOME
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diskclean as dc  # noqa: E402


def mk(path, size=0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(os.urandom(size))


class SafetyTests(unittest.TestCase):
    def setUp(self):
        for d in ["Documents/proj/node_modules", "Library/Caches/foo", "Library/Keychains/x",
                  "Library/Mobile Documents/doc", "proj/.git", "Library/Containers/com.docker.docker/Data"]:
            os.makedirs(os.path.join(FAKE_HOME, d), exist_ok=True)

    def ok(self, rel):
        return dc.is_deletable(os.path.join(FAKE_HOME, rel))[0]

    def test_allows_regenerable_items(self):
        self.assertTrue(self.ok("Documents/proj/node_modules"))
        self.assertTrue(self.ok("Library/Caches/foo"))

    def test_blocks_core_folders(self):
        for rel in ["", "Documents", "Library", "Library/Caches", ".Trash"]:
            self.assertFalse(dc.is_deletable(os.path.join(FAKE_HOME, rel).rstrip("/"))[0], rel)

    def test_blocks_sensitive_locations(self):
        self.assertFalse(self.ok("Library/Keychains/x"))
        self.assertFalse(self.ok("Library/Mobile Documents/doc"))
        self.assertFalse(self.ok("Library/Containers/com.docker.docker/Data"))
        self.assertFalse(self.ok("proj/.git"))

    def test_blocks_outside_home_and_tricks(self):
        self.assertFalse(dc.is_deletable("/etc")[0])
        self.assertFalse(dc.is_deletable(FAKE_HOME + "/Documents/../../etc")[0])
        self.assertFalse(dc.is_deletable("Documents/proj")[0])
        self.assertFalse(dc.is_deletable(FAKE_HOME + "/missing")[0])
        self.assertFalse(dc.is_deletable(None)[0])

    def test_blocks_symlinked_parent_escaping_home(self):
        outside = tempfile.mkdtemp()
        os.makedirs(os.path.join(outside, "victim"))
        link = os.path.join(FAKE_HOME, "escape")
        if not os.path.lexists(link):
            os.symlink(outside, link)
        self.assertFalse(dc.is_deletable(os.path.join(link, "victim"))[0])


class ScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.join(FAKE_HOME, "scanroot")
        mk(os.path.join(cls.root, "app/package.json"), 10)
        mk(os.path.join(cls.root, "app/node_modules/big/a.bin"), 3_000_000)
        mk(os.path.join(cls.root, "app/node_modules/inner/node_modules/b.bin"), 1_000_000)
        mk(os.path.join(cls.root, "app/.next/cache/c.pack"), 2_000_000)
        mk(os.path.join(cls.root, "flutter/pubspec.yaml"), 10)
        mk(os.path.join(cls.root, "flutter/build/out.bin"), 1_500_000)
        mk(os.path.join(cls.root, "notflutter/build/keep.bin"), 1_500_000)
        mk(os.path.join(cls.root, "photos/movie.mov"), 4_000_000)
        for i in range(30):
            mk(os.path.join(cls.root, f"tiny/f{i}.txt"), 100)
        cls.scan = dc.Scan(cls.root)
        cls.scan.run()

    def test_total_matches_du(self):
        import subprocess
        du = int(subprocess.run(["du", "-sk", self.root], capture_output=True, text=True).stdout.split()[0]) * 1024
        self.assertAlmostEqual(self.scan.tree.size, du, delta=64 * 1024)

    def test_candidates_detected_without_nesting(self):
        found = {os.path.relpath(p, self.root): k for p, (k, _) in self.scan.candidates.items()}
        self.assertEqual(found.get("app/node_modules"), "node_modules")
        self.assertEqual(found.get("app/.next"), "next")
        self.assertEqual(found.get("flutter/build"), "build_output")
        self.assertNotIn("notflutter/build", found)
        self.assertNotIn("app/node_modules/inner/node_modules", found)

    def test_largest_files_and_folding(self):
        top = dc.largest_files(self.scan.tree)
        self.assertEqual(top[0]["name"], "movie.mov")
        tiny, _ = self.scan.find(os.path.join(self.root, "tiny"))
        self.assertIsNone(tiny)  # folded into "smaller items"
        self.assertEqual(self.scan.tree.other_count, 1)

    def test_remove_updates_sizes(self):
        scan = dc.Scan(self.root)
        scan.run()
        nm = os.path.join(self.root, "app/node_modules")
        node, _ = scan.find(nm)
        before_root, before_app = scan.tree.size, scan.find(os.path.join(self.root, "app"))[0].size
        scan.remove(nm, node.size)
        self.assertEqual(scan.tree.size, before_root - node.size)
        app = scan.find(os.path.join(self.root, "app"))[0]
        self.assertEqual(app.size, before_app - node.size)
        self.assertIsNone(scan.find(nm)[0])
        self.assertNotIn(nm, scan.candidates)

    def test_suggestions(self):
        sugg = dc.build_suggestions(self.scan)  # all below 50 MB threshold
        self.assertEqual(sugg, [])
        old = dc.MIN_SUGGEST
        dc.MIN_SUGGEST = 1
        try:
            sugg = dc.build_suggestions(self.scan)
        finally:
            dc.MIN_SUGGEST = old
        paths = [s["path"] for s in sugg]
        self.assertIn(os.path.join(self.root, "app/node_modules"), paths)
        sizes = [s["size"] for s in sugg]
        self.assertEqual(sizes, sorted(sizes, reverse=True))


class RemoveTests(unittest.TestCase):
    def test_trash_and_delete(self):
        os.makedirs(os.path.join(FAKE_HOME, ".Trash"), exist_ok=True)
        a = os.path.join(FAKE_HOME, "work/a/node_modules")
        mk(os.path.join(a, "x.bin"), 1000)
        dc.move_to_trash(a)
        self.assertFalse(os.path.exists(a))
        self.assertTrue(os.path.exists(os.path.join(FAKE_HOME, ".Trash/node_modules/x.bin")))
        b = os.path.join(FAKE_HOME, "work/b/.next")
        mk(os.path.join(b, "ro.bin"), 10)
        os.chmod(os.path.join(b, "ro.bin"), 0o400)
        dc.delete_forever(b)
        self.assertFalse(os.path.exists(b))


if __name__ == "__main__":
    unittest.main()
