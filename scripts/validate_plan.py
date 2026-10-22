#!/usr/bin/env python3
"""Validate an independent-footage shot ledger; never reads or writes source files."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


class PlanError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PlanError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def records(plan, key):
    items = plan.get(key)
    require(isinstance(items, list), f'{key} must be an array')
    result = {}
    for item in items:
        require(isinstance(item, dict), f'{key} entries must be objects')
        ident = item.get('id')
        require(nonempty(ident), f'{key} entries need a nonempty id')
        require(ident not in result, f'duplicate {key} id: {ident}')
        result[ident] = item
    return result


def references(item, context):
    ids = item.get('shot_ids')
    require(isinstance(ids, list) and all(nonempty(x) for x in ids),
            f'{context}: shot_ids must be an array of nonempty strings')
    require(len(ids) == len(set(ids)), f'{context}: duplicate shot_ids')
    return ids


def summarize(shots):
    counts = Counter((s['delivery'], s['status']) for s in shots)
    return {
        'onsite_ready': counts['onsite', 'ready'],
        'onsite_conditional': counts['onsite', 'conditional'],
        'onsite_total': sum(counts['onsite', state] for state in ('ready', 'conditional')),
        'ai_total': sum(counts['ai', state] for state in ('ready', 'conditional')),
        'ai_conditional': counts['ai', 'conditional'],
        'external_total': sum(counts['external', state] for state in ('ready', 'conditional')),
        'external_conditional': counts['external', 'conditional'],
        'speech_segments': len({s['speech_id'] for s in shots if s.get('speech_id')}),
        'speech_shots': sum(bool(s.get('speech_id')) for s in shots),
    }


def validate(plan):
    require(isinstance(plan, dict), 'plan must be an object')
    rows = records(plan, 'source_rows')
    shots = records(plan, 'shots')
    groups = records(plan, 'groups')
    require(rows, 'source_rows must not be empty')
    source_coverage = []
    for ident, row in rows.items():
        for field in ('script', 'sheet', 'row'):
            require(nonempty(row.get(field)), f'{ident}: missing {field}')
        ids = references(row, ident)
        unresolved = row.get('unresolved')
        no_shot = row.get('no_shot_reason')
        for field in ('unresolved', 'no_shot_reason'):
            if field in row:
                require(nonempty(row[field]), f'{ident}: {field} must be nonempty text')
        require(not (unresolved and no_shot), f'{ident}: conflicting row reasons')
        require(not (ids and no_shot), f'{ident}: no_shot_reason conflicts with shots')
        require(ids or unresolved or no_shot, f'{ident}: no shots and no explanation')
        for sid in ids:
            require(sid in shots, f'{ident}: unknown shot {sid}')
            require(shots[sid].get('source_row') == ident,
                    f'{sid}: source_row disagrees with source_rows inventory')
        source_coverage.extend(ids)
    require(Counter(source_coverage) == Counter({sid: 1 for sid in shots}),
            'every shot must be listed in exactly one source row')

    speech_scripts = {}
    for sid, shot in shots.items():
        require(nonempty(shot.get('description')), f'{sid}: missing description')
        require(shot.get('delivery') in ('onsite', 'ai', 'external'),
                f'{sid}: invalid delivery')
        require(shot.get('status') in ('ready', 'conditional'), f'{sid}: invalid status')
        if shot['status'] == 'conditional':
            require(nonempty(shot.get('condition')), f'{sid}: conditional shot needs condition')
        if 'speech_id' in shot:
            speech = shot['speech_id']
            require(nonempty(speech), f'{sid}: speech_id must be nonempty text')
            require(shot['delivery'] == 'onsite', f'{sid}: speech_id is for onsite dialogue only')
            script = rows[shot['source_row']]['script']
            require(speech not in speech_scripts or speech_scripts[speech] == script,
                    f'{speech}: cannot share a speech_id across scripts')
            speech_scripts[speech] = script

    assignment = []
    speech_groups = set()
    for gid, group in groups.items():
        require(nonempty(group.get('label')), f'{gid}: missing label')
        ids = references(group, gid)
        require(ids, f'{gid}: empty shooting group')
        for sid in ids:
            require(sid in shots, f'{gid}: unknown shot {sid}')
            require(shots[sid]['delivery'] == 'onsite', f'{gid}: non-onsite shot {sid}')
            if shots[sid].get('speech_id'):
                speech_groups.add(gid)
        assignment.extend(ids)
    expected = {sid for sid, shot in shots.items() if shot['delivery'] == 'onsite'}
    require(Counter(assignment) == Counter({sid: 1 for sid in expected}),
            'every onsite shot must appear in exactly one group (no omission or reuse)')
    if 'speech_grouping_exception' in plan:
        require(nonempty(plan['speech_grouping_exception']), 'grouping exception needs a reason')
    require(len(speech_groups) <= 1 or nonempty(plan.get('speech_grouping_exception')),
            'dialogue is split across groups; group it or explain the exception')

    per_script = {}
    for row in rows.values():
        per_script.setdefault(row['script'], [])
        per_script[row['script']].extend(shots[sid] for sid in row['shot_ids'])
    unresolved = [ident for ident, row in rows.items() if row.get('unresolved')]
    return {
        'validation': 'PASS',
        'scope': 'ledger structure and counts only; source semantics require human/agent review',
        'totals': summarize(list(shots.values())),
        'unresolved_rows': unresolved,
        'per_script': {key: summarize(value) for key, value in per_script.items()},
        'groups': [dict(id=gid, label=g['label'], **summarize([shots[sid] for sid in g['shot_ids']]))
                   for gid, g in groups.items()],
        'speech_grouping_exception': plan.get('speech_grouping_exception'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, help='UTF-8 JSON shot ledger')
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.plan.read_text(encoding='utf-8')))
    except (OSError, UnicodeError, json.JSONDecodeError, PlanError) as exc:
        print(json.dumps({'validation': 'FAIL', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
