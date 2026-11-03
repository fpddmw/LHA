"""Offline tests for the layered (v2) experience catalog and its held-out hygiene."""
import copy, json, re, subprocess, sys, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness.creative_knowledge import CreativeKnowledge, layered_fields
from planner_harness.experience_contributions import navigation_documents
import build_experience_catalog as builder

CURATED = ROOT / "knowledge/experience/curated"


class LayeredCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((CURATED / "catalog.json").read_text())

    def test_catalog_is_v2_and_every_entry_has_a_layer(self):
        self.assertEqual(self.catalog["schema"], "creative-experience-catalog-v2")
        layers = {e["id"]: e["layer"] for e in self.catalog["entries"]}
        self.assertEqual(set(layers.values()), {"principle", "renderer", "condition"})
        order = [e["layer"] for e in self.catalog["entries"]]
        self.assertEqual(order, sorted(order, key=("principle", "renderer", "condition").index))

    def test_checked_in_catalog_matches_its_sources(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/build_experience_catalog.py"), "--check"],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_map_orders_principles_before_renderers_before_conditions(self):
        text = (CURATED / "README.md").read_text()
        positions = [text.index(h) for h in ("## Common principles", "## Bernini capabilities", "## Ditto capabilities", "## Conditions of the task")]
        self.assertEqual(positions, sorted(positions))
        docs = navigation_documents(self.catalog)
        self.assertIn("Common principles", json.dumps(docs))

    def test_every_entry_keeps_all_renderers_visible_not_filtered(self):
        for entry in self.catalog["entries"]:
            if entry["layer"] == "principle":
                self.assertEqual(set(entry["renderers"]), {"bernini", "ditto"})

    def test_layer_validation_rejects_unknown_values(self):
        with self.assertRaises(ValueError): layered_fields({"layer": "mystery"})
        with self.assertRaises(ValueError): layered_fields({"tracks": ["medium"]})
        with self.assertRaises(ValueError): layered_fields({"stages": ["win"]})
        self.assertEqual(layered_fields({}), "principle")

    def test_v1_catalog_without_layers_still_loads(self):
        v1 = {"schema": "creative-experience-catalog-v1", "revision": "legacy", "entries": [], "resources": []}
        self.assertEqual(layered_fields({}), "principle")
        nav = navigation_documents(v1)
        self.assertTrue(nav)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.json'
            CreativeKnowledge(ROOT).freeze(path)
            saved=json.loads(path.read_text())
            saved['curated_catalog']['schema']='creative-experience-catalog-v1'
            for row in saved['curated_catalog']['entries']:
                for field in ('layer','tracks','families','stages'):row.pop(field,None)
            restored=CreativeKnowledge(ROOT,saved)
            self.assertIn('EX-P-every-plane',restored.items)
            self.assertIn('Rebuild every plane',restored.read('EX-P-every-plane')['text'])

    def test_none_mode_exposes_no_experience(self):
        full = CreativeKnowledge(ROOT, experience_mode="full")
        none = CreativeKnowledge(ROOT, experience_mode="none")
        self.assertEqual(len(full.curated_catalog["entries"]), len(self.catalog["entries"]))
        self.assertEqual(none.curated_catalog["entries"], [])
        for entry in self.catalog["entries"]:
            self.assertIn(entry["id"], full.items)
            self.assertNotIn(entry["id"], none.items)
        for old in ("choose-editing-input", "express-edits", "inspect-and-compare", "use-design-knowledge"):
            for k in (full, none):
                with self.assertRaises(ValueError): k.read(old)

    def test_none_manuals_carry_method_without_experience_links(self):
        for name in ("UNDERSTAND_AND_DESIGN.md", "UNDERSTAND_AND_REVISE.md", "README.md", "READING.md"):
            text = (ROOT / "knowledge/creative-loop/no-experience" / name).read_text()
            self.assertNotIn("experience/curated", text)
        design = (ROOT / "knowledge/creative-loop/no-experience/UNDERSTAND_AND_DESIGN.md").read_text()
        self.assertIn("planes", design)

    def test_no_entry_text_or_evidence_cites_a_heldout_source(self):
        blocked = builder.heldout_hashes()
        self.assertTrue(blocked)
        for path in (CURATED / "evidence").glob("*.json"):
            builder.check_evidence(path, blocked)
        for path in (CURATED / "entries").glob("*.md"):
            text = path.read_text()
            self.assertFalse(set(re.findall(r"[0-9a-f]{64}", text)) & set(blocked), path.name)

    def test_builder_rejects_evidence_with_heldout_hash(self):
        blocked = builder.heldout_hashes()
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"video_sha256": next(iter(blocked))}))
            with self.assertRaises(SystemExit): builder.check_evidence(bad, blocked)

    def test_entries_name_their_evidence_and_it_exists(self):
        resources = {r["id"] for r in self.catalog["resources"]}
        for entry in self.catalog["entries"]:
            self.assertTrue(entry["evidence_ids"], entry["id"])
            self.assertLessEqual(set(entry["evidence_ids"]), resources, entry["id"])


class TaskTrackExposureTests(unittest.TestCase):
    def test_execution_profile_projection_includes_task_track(self):
        source = (ROOT / "src/planner_harness/context.py").read_text()
        self.assertIn('"task_track"', source)


class BuilderChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.curated=self.root/'knowledge/experience/curated'
        (self.curated/'entries').mkdir(parents=True)
        (self.root/'benchmark_data').mkdir()
        (self.root/'benchmark_data/benchmark.json').write_text(json.dumps([
            {'sample_id':'001','split':'train','source_video_sha256':'a'*64},
            {'sample_id':'067','split':'test','source_video_sha256':'b'*64}]))
        self.entry=self.curated/'entries/P-fixture.md'
        self.meta={'id':'EX-P-fixture','title':'Fixture','summary':'Prefer the fixture construction.',
                   'questions':['Which fixture?'],'renderers':['bernini'],'layer':'principle',
                   'evidence_ids':[],'review_reference':'software-fixture'}
        self.entry.write_text('<!-- meta '+json.dumps(self.meta)+' -->\n# Fixture\n\nPractical fixture account.\n')
        (self.curated/'catalog.json').write_text(json.dumps({'schema':builder.SCHEMA,'entries':[],'resources':[]}))
        self.roots=patch.multiple(builder,ROOT=self.root,CURATED=self.curated);self.roots.start()
        builder.build()

    def tearDown(self):
        self.roots.stop();self.tmp.cleanup()

    def test_check_detects_catalog_and_navigation_drift_without_writing(self):
        builder.build(write=False)
        catalog=self.curated/'catalog.json';original=catalog.read_text()
        data=json.loads(original);data['entries'][0]['summary']='Stale summary.'
        catalog.write_text(json.dumps(data));tampered=catalog.read_bytes()
        with self.assertRaisesRegex(SystemExit,'Catalog differs'):builder.build(write=False)
        self.assertEqual(catalog.read_bytes(),tampered)
        catalog.write_text(original)
        nav=self.curated/'README.md';nav.write_text('Stale map.\n')
        with self.assertRaisesRegex(SystemExit,'navigation is stale'):builder.build(write=False)
        self.assertEqual(nav.read_text(),'Stale map.\n')

    def test_text_hash_split_and_path_provenance_are_checked(self):
        for name,text in [('heldout.md','Observed source: '+'b'*64),
                          ('heldout.txt','Video benchmark_data/test/067/video.mp4'),
                          ('heldout.json',json.dumps({'split':'test'})),
                          ('sample.json',json.dumps({'sample_id':'067'})),
                          ('sample.md','sample_id: 067'),
                          ('embedded.json',json.dumps({'notes':'Observed '+'b'*64+' here'}))]:
            path=self.root/name;path.write_text(text)
            with self.subTest(name=name),self.assertRaises(SystemExit):
                builder.check_evidence(path,builder.heldout_hashes())
        self.entry.write_text(self.entry.read_text()+'\nObserved '+('b'*64))
        with self.assertRaisesRegex(SystemExit,'held-out'):builder.build()

    def test_builder_validates_placement_and_reading_links(self):
        for field,value in [('tracks',['medium']),('stages',['win']),('families','craft')]:
            self.entry.write_text('<!-- meta '+json.dumps({**self.meta,field:value})+' -->\n# Fixture\n')
            with self.subTest(field=field),self.assertRaises(SystemExit):builder.build()
        self.entry.write_text('<!-- meta '+json.dumps(self.meta)+' -->\n[Old entry](missing.md)\n')
        with self.assertRaisesRegex(SystemExit,'broken local reading link'):builder.build()


if __name__ == "__main__":
    unittest.main()
