import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts/validate_plan.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
EXAMPLE = json.loads((ROOT / 'references/example-plan.json').read_text(encoding='utf-8'))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.plan = copy.deepcopy(EXAMPLE)

    def reject(self, message):
        with self.assertRaisesRegex(validator.PlanError, message):
            validator.validate(self.plan)

    def test_example_preserves_independent_footage(self):
        result = validator.validate(self.plan)
        self.assertEqual(result['totals']['onsite_total'], 7)
        self.assertEqual(result['totals']['onsite_ready'], 6)
        self.assertEqual(result['totals']['onsite_conditional'], 1)
        self.assertEqual(result['totals']['ai_total'], 1)
        self.assertEqual(result['totals']['speech_segments'], 2)
        self.assertEqual(result['groups'][1]['onsite_total'], 4)
        self.assertEqual(sum(g['onsite_total'] for g in result['groups']), 7)
        self.assertEqual(sum(s['onsite_total'] for s in result['per_script'].values()), 7)

    def test_duplicate_shot_id(self):
        self.plan['shots'].append(self.plan['shots'][0])
        self.reject('duplicate shots id')

    def test_omission(self):
        self.plan['groups'][1]['shot_ids'].pop()
        self.reject('exactly one group')

    def test_reuse_across_groups(self):
        self.plan['groups'][1]['shot_ids'].append('A-r2a')
        self.reject('exactly one group')

    def test_ai_is_not_onsite(self):
        self.plan['groups'][1]['shot_ids'].append('B-r5a')
        self.reject('non-onsite')

    def test_condition_required(self):
        del self.plan['shots'][6]['condition']
        self.reject('needs condition')

    def test_speech_must_stay_together(self):
        self.plan['groups'][0]['shot_ids'].remove('B-r2a')
        self.plan['groups'][1]['shot_ids'].append('B-r2a')
        self.reject('dialogue is split')
        self.plan['speech_grouping_exception'] = 'B段依赖拆件状态；已向用户说明'
        validator.validate(self.plan)

    def test_source_inventory_omission(self):
        self.plan['source_rows'][1]['shot_ids'].pop()
        self.reject('exactly one source row')

    def test_source_mismatch(self):
        self.plan['shots'][1]['source_row'] = 'B-r3'
        self.reject('disagrees')

    def test_unknown_row_remains_visible(self):
        self.plan['source_rows'].append(dict(id='B-r6', script='虚构脚本B', sheet='脚本',
                                            row='6', shot_ids=[], unresolved='源句不完整，数量未定'))
        result = validator.validate(self.plan)
        self.assertEqual(result['unresolved_rows'], ['B-r6'])
        self.assertEqual(result['totals']['onsite_total'], 7)

    def test_unexplained_empty_row(self):
        self.plan['source_rows'][0]['shot_ids'] = []
        self.reject('no shots and no explanation')

    def test_malformed_input(self):
        self.plan['groups'][0]['shot_ids'] = 'A-r2a'
        self.reject('must be an array')

    def test_external_conditions_are_separate(self):
        self.plan['shots'][-1].update(delivery='external', status='conditional', condition='等待授权素材')
        totals = validator.validate(self.plan)['totals']
        self.assertEqual(totals['onsite_total'], 7)
        self.assertEqual(totals['external_total'], 1)
        self.assertEqual(totals['external_conditional'], 1)

    def test_speech_id_not_shared_across_scripts(self):
        self.plan['shots'][3]['speech_id'] = 'A-speech1'
        self.reject('across scripts')


if __name__ == '__main__':
    unittest.main()
