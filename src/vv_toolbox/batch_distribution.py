"""Empirical requested-parameter distributions, separated by attempt outcome."""
from collections import Counter
from itertools import combinations
import math


def _summarize(candidates):
    groups = {}
    malformed = 0
    baseline_count = 0
    for candidate in candidates:
        if not isinstance(candidate, list):
            malformed += 1
            continue
        if not candidate:
            baseline_count += 1
            continue
        for operation in candidate:
            if not isinstance(operation, dict):
                malformed += 1
                continue
            # Preserve measurement definitions and anatomical regions: unlike
            # units and severity definitions must never share a distribution.
            kind = operation.get('type', 'concentric_stenosis')
            region = operation.get('region')
            method = operation.get('measurement_method',
                'local_baseline_diameter_ratio' if kind == 'fusiform_dilation' else None)
            if any(value is not None and not isinstance(value, str)
                   for value in (kind, region, method)):
                malformed += 1
                continue
            key = (kind, region, method)
            group = groups.setdefault(key, {'operation_count': 0, 'numeric': {}, 'rows': []})
            group['operation_count'] += 1
            row = {}
            for field, value in operation.items():
                if type(value) is int or (type(value) is float and math.isfinite(value)):
                    group['numeric'].setdefault(field, []).append(value)
                    row[field] = value
            group['rows'].append(row)
    result = []
    for (kind, region, method), group in sorted(groups.items(), key=lambda item: repr(item[0])):
        fields = {}
        for field, values in sorted(group['numeric'].items()):
            counts = Counter(values)
            fields[field] = {'count': len(values), 'missing_count': group['operation_count']-len(values),
                'min': min(values), 'max': max(values),
                'empirical_values': [{'value': value, 'count': count}
                                     for value, count in sorted(counts.items())]}
        pairs = []
        for first, second in combinations(sorted(fields), 2):
            counts = Counter((row[first], row[second]) for row in group['rows']
                             if first in row and second in row)
            complete = sum(counts.values())
            pairs.append({'fields': [first, second], 'count': complete,
                'missing_count': group['operation_count']-complete,
                'empirical_values': [{'values': list(values), 'count': count}
                                     for values, count in sorted(counts.items())]})
        result.append({'type': kind, 'region': region, 'measurement_method': method,
                       'operation_count': group['operation_count'], 'parameters': fields,
                       'parameter_pairs': pairs})
    return {'candidate_count': len(candidates), 'malformed_entry_count': malformed,
            'baseline_candidate_count': baseline_count, 'groups': result}


def parameter_distribution(candidates, attempts):
    """Count requested operations; failed-case operations are all rejected.

    Unattempted candidates are not failures. Samples are not independent
    subjects and these counts do not assert a clinical population distribution.
    """
    attempted = [record['parameters'] for record in attempts]
    return {'schema': 'vv-toolbox.batch-distribution/1',
        'scope': 'requested parameters; operation-weighted within each candidate outcome',
        'population_inference': 'NONE',
        'candidate_pool': _summarize(candidates),
        'attempted': _summarize(attempted),
        'accepted': _summarize([r['parameters'] for r in attempts if r['status'] == 'PASS']),
        'rejected': _summarize([r['parameters'] for r in attempts if r['status'] == 'FAIL']),
        'unattempted': _summarize(candidates[len(attempts):])}
