"""Resolve explicit source role bindings through recorded split/trim lineage."""
from .case_contract import validate_case


def resolve_source_roles(case, source_roles, *, allow_declared_omissions=False):
    """Return active descendants only; never infer anatomy from names or distance."""
    validate_case(case)
    if not isinstance(source_roles, dict) or not source_roles:
        raise ValueError('explicit source roles required')
    if any(not isinstance(role, str) or not role or not isinstance(ids, list) or not ids
           or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids)
           for role, ids in source_roles.items()):
        raise ValueError('unique source edge IDs required per role')
    parents = {}
    records = list(case['edges'])
    records += [h['parent_edge'] for h in case.get('synthetic_junctions', {}).get('history', []) if 'parent_edge' in h]
    omissions = set()
    for history in case.get('synthetic_trunk_simplifications', []):
        records.extend(history['original_edges'])
        omitted = history['omitted_edge_id']
        spec = history['specification']
        if omitted != spec['omit_edge_id'] or not spec['evidence_refs'] or not spec['rationale'] or not any(e['id'] == omitted for e in history['original_edges']):
            raise ValueError('invalid declared omission record')
        omissions.add(omitted)
    for edge in records:
        parent = edge.get('derived_interval', {}).get('parent_edge_id')
        links = edge.get('merged_parent_edge_ids', [] if parent is None else [parent])
        if not links:
            continue
        if not isinstance(links, list) or not all(isinstance(p, str) and p and p != edge['id'] for p in links) or len(set(links)) != len(links):
            raise ValueError('invalid source lineage')
        if edge['id'] in parents and parents[edge['id']] != links:
            raise ValueError('ambiguous source lineage')
        parents[edge['id']] = links

    def ancestors(ident, trail=frozenset()):
        if ident in trail:
            raise ValueError('cyclic source lineage')
        found = {ident}
        for parent in parents.get(ident, []):
            found.update(ancestors(parent, trail | {ident}))
        return found

    ancestry = {e['id']: ancestors(e['id']) for e in case['edges']}
    result = {}
    for role, originals in source_roles.items():
        for original in originals:
            if not any(original in chain for chain in ancestry.values()):
                if allow_declared_omissions and original in omissions:
                    continue
                raise ValueError(f'missing active descendant for {role}: {original}')
        result[role] = sorted(ident for ident, chain in ancestry.items() if set(originals) & chain)
        if not result[role]:
            raise ValueError('omissions cannot remove an entire required role: '+role)
    return result
