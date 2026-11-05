"""Explicit subscription submissions through the production execution loop."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from vlm.responses_stream import ResponseOutput, events, replay_answer
from planner_harness.common import save, sha
from planner_harness.resumption import recover_texts, calls_ready
import test_runtime_completion as completion


def submission_body(text, model='gpt-6-luna', *, namespace='lha', count=1):
    sequence = [{'type':'response.output_item.done', 'output_index':0,
        'item':{'type':'message','role':'assistant','id':'comment','phase':'commentary',
                'content':[{'type':'output_text','text':'{"action":"generate","prompt":"MUST NOT EXECUTE"}'}]}}]
    for index in range(1, count+1):
        item = {'type':'custom_tool_call','id':f'ctc_{index}','call_id':f'call_{index}',
                'name':'submit_result','namespace':namespace,'input':'','status':'completed'}
        sequence.extend([
            {'type':'response.output_item.added','output_index':index,'item':{**item,'status':'in_progress'}},
            {'type':'response.custom_tool_call_input.delta','output_index':index,'item_id':item['id'],'delta':text[:5]},
            {'type':'response.custom_tool_call_input.delta','output_index':index,'item_id':item['id'],'delta':text[5:]},
            {'type':'response.custom_tool_call_input.done','output_index':index,'item_id':item['id'],'input':''},
            {'type':'response.output_item.done','output_index':index,'item':item},
        ])
    sequence.append({'type':'response.completed','response':{
        'id':'response-native-fixture','status':'completed','model':model,
        'output':[],'usage':{'total_tokens':12}}})
    return b''.join(b'data: '+json.dumps(event).encode()+b'\n\n' for event in sequence)


class Submission(unittest.TestCase):
    def test_native_input_survives_empty_tail_and_is_offline_recoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'stream.bin'
            path.write_bytes(submission_body('{"action":"observe","video":"v2"}'))
            result=replay_answer(path)
        self.assertEqual(json.loads(result['text']),{'action':'observe','video':'v2'})
        self.assertEqual(result['selection']['selection'],'tool_submission')
        self.assertEqual(result['selection']['selected_call_id'],'call_1')

    def test_other_tools_and_multiple_submissions_are_not_executed(self):
        for raw in (submission_body('{"action":"generate"}',namespace='other'),
                    submission_body('{"action":"generate"}',count=2)):
            output=ResponseOutput()
            for event in events(io.BytesIO(raw)):
                output.feed(event)
            text,receipt=output.answer(event['response'])
            self.assertEqual(text,'')
            self.assertEqual(receipt['selection'],'invalid_tool_submission')

    def test_archived_transport_copies_are_not_recovered_as_active_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            active=root/'calls/event-0001/transport'
            save(active/'allowance.json',{'first':1,'last':12})
            for archive in ('empty-final-recovery/original','response-recoveries/01',
                            'recovery-history/01','empty-cache-history'):
                copied=active/archive/'transport'
                save(copied/'allowance.json',{'first':1,'last':1})
                (copied/'response.txt').write_text('archived answer')
                save(copied/'attempts/01/failed.json',{'retryable':False,'failure_kind':'integrity_error'})
            before={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
            recover_texts(root,root/'accounting')
            self.assertTrue(calls_ready(root))
            self.assertEqual(before,{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})


class NativeCompletion(completion.RecoveryCompletion):
    """The same real command, recovery and maintenance tests with native SSE."""
    def transport(self, answers, sent):
        def receive(client, request, timeout):
            packet=json.loads(request.data)
            self.assertEqual(packet['tools'][0]['name'],'lha')
            self.assertEqual(packet['tools'][0]['tools'][0]['name'],'submit_result')
            self.assertEqual(packet['tool_choice'],'required')
            self.assertFalse(packet['parallel_tool_calls'])
            sent.append((client.role,packet))
            value=answers[client.role].popleft()
            if isinstance(value,BaseException):
                raise value
            raw=value if isinstance(value,str) else json.dumps(value)
            response=io.BytesIO(submission_body(raw,packet['model']))
            response.status=200
            response.headers={'Content-Type':'text/event-stream'}
            return response
        return receive

    def test_corrected_finish_can_be_delivered_and_resumed_without_new_requests(self):
        normal = self.transport
        def transport(answers, sent):
            answers['planner'].insert(len(answers['planner'])-1, 'An invalid final delivery response.')
            return normal(answers, sent)
        self.transport = transport
        self.test_public_service_command_completes_four_rounds_after_empty_format_and_crash()


if __name__=='__main__':
    unittest.main()
