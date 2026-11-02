import unittest
from unittest.mock import patch
from test_unified_results import Fixture
from planner_harness.common import save, sha
from planner_harness.execution import signature
from import_renderer_results import ingest

class ImportTests(Fixture):
    def fixture(self, renderer):
        run=self.output
        runtime={"renderer":"Ditto global LoRA", "runner":"ditto-adapted-pe-v2"} if renderer=="ditto" else {"runner":"bernini-benchmark-v3", "bernini_sources":{}}
        case={"sample_id":"001", "tier":"short", "condition":"pe", "seed":42,
            "case_id":"001__short__pe", "prompt":self.rows[0]["prompt_short"], "source_sha256":sha(self.source)}
        body={"cases":[case], "generation":{"steps":40}}
        plan={**body,"sha256":signature(body)}
        save(run/"plan.json",plan);save(run/"runtime.json",runtime)
        folder=run/"cases"/case["case_id"];folder.mkdir(parents=True,exist_ok=True)
        (folder/"native.mp4").write_bytes(self.source.read_bytes())
        binding={"case":case,"plan_sha256":plan["sha256"],"runtime_sha256":signature(runtime)}
        save(folder/"input.json",binding)
        save(folder/"result.json",{"status":"complete","input_sha256":signature(binding),
            "input_file_sha256":sha(folder/"input.json"),"output_sha256":sha(folder/"native.mp4"),"artifact_hashes":{}})
        return run,folder

    def test_both_formats_and_idempotence(self):
        for renderer in ("bernini","ditto"):
            run,folder=self.fixture(renderer)
            collection=self.registry/renderer
            with patch("import_renderer_results.report",return_value={}):
                ingest(self.repo,collection,run,renderer)
                ingest(self.repo,collection,run,renderer)
            self.assertEqual(len(list((collection/"entries").glob("*/*/*/*.json"))),1)

    def test_runtime_and_video_tampering(self):
        run,folder=self.fixture("ditto")
        save(run/"runtime.json",{"renderer":"Ditto changed"})
        with self.assertRaises(ValueError):ingest(self.repo,self.registry,run,"ditto")
        run,folder=self.fixture("ditto")
        (folder/"native.mp4").write_bytes(b"changed")
        with self.assertRaises(ValueError):ingest(self.repo,self.registry,run,"ditto")

    def test_wrong_renderer(self):
        run,_=self.fixture("ditto")
        with self.assertRaises(ValueError):ingest(self.repo,self.registry,run,"bernini")

if __name__=="__main__":unittest.main()
