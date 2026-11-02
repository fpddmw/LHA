"""Run a de-duplicated offline suite with source/test snapshot hashes."""
import argparse
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
def snapshot():
    files=list((ROOT/'src').rglob('*.py'))+list((ROOT/'src').rglob('*.md'))+list((ROOT/'scripts').glob('*.py'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from flatten(test)
        else:yield test
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('modules',nargs='+');args=p.parse_args()
before=snapshot();selected={}
for name in args.modules:
    for test in flatten(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))):
        key=(str(Path(inspect.getfile(type(test))).resolve()),type(test).__qualname__,test._testMethodName)
        selected.setdefault(key,test)
started=time.time()
with args.output.with_suffix('.log').open('w') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(selected.values()))
after=snapshot();record={'modules':args.modules,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':time.time()-started,'source_test_stable':before==after,'changes':{k:[before.get(k),after.get(k)] for k in before.keys()|after.keys() if before.get(k)!=after.get(k)},'start_files':before,'end_files':after,'unique_tests':[list(k) for k in selected]}
args.output.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in {'start_files','end_files','unique_tests'}}));sys.exit(0 if result.wasSuccessful() else 1)
