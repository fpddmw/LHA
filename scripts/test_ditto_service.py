"""CPU checks for source/candidate time axes and frozen Ditto configuration."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from server_runtime.ditto import conditioning_indices, PersistentDittoRenderer

class TimingTests(unittest.TestCase):
    def setUp(self):
        self.payload={'input_id':'source','renderer':{'output':{'frames':5,'fps':20,'width':848,'height':480},
            'conditioning_source_indices':[0,2,4,6,8]}}
        self.source={'frames':10,'fps':40,'width':1280,'height':720}
    def test_source_profile_and_candidate_identity(self):
        self.assertEqual(conditioning_indices(self.payload,self.source),[0,2,4,6,8])
        self.payload['input_id']='v1'
        self.assertEqual(conditioning_indices(self.payload,{'frames':5,'fps':20,'width':848,'height':480}),list(range(5)))
    def test_reject_candidate_time_or_geometry_drift(self):
        self.payload['input_id']='v2'
        for field,value in [('frames',9),('fps',24),('width',832),('height',464)]:
            info={'frames':5,'fps':20,'width':848,'height':480};info[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):conditioning_indices(self.payload,info)
    def test_source_indices_are_explicit_bounded_and_ordered(self):
        for indices in [None,[0,1],[0,2,4,6,10],[0,2,6,4,8],[0,2,4,6,8.0]]:
            payload=copy.deepcopy(self.payload);payload['renderer']['conditioning_source_indices']=indices
            with self.subTest(indices=indices),self.assertRaises(ValueError):conditioning_indices(payload,self.source)
    def test_reject_silent_profile_changes(self):
        cfg={'backend':'ditto','generation':{'num_inference_steps':50,'cfg_scale':5.0,'lora_alpha':1.0,
            'negative_prompt':'','prompt_enhancer':False,'tiled':True,'precision':'bfloat16'}}
        self.assertFalse(PersistentDittoRenderer('.',cfg,'.').ready)
        for field,value in [('num_inference_steps',30),('prompt_enhancer',True),('unknown_setting',1)]:
            changed=copy.deepcopy(cfg);changed['generation'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):PersistentDittoRenderer('.',changed,'.')

if __name__=='__main__':unittest.main()
