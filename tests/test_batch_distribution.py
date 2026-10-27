from vv_toolbox.batch_distribution import parameter_distribution


def test_definitions_regions_and_operation_weighting_are_separate():
    diameter = dict(region='aca', measurement_method='local_baseline_diameter', severity_percent=40)
    area = dict(diameter, measurement_method='local_baseline_area')
    dilation = dict(type='fusiform_dilation', region='aca', diameter_ratio=2)
    other_region = dict(diameter, region='femoral')
    candidates = [[diameter, diameter, area, dilation, other_region], [diameter]]
    summary = parameter_distribution(candidates, [dict(parameters=candidates[0], status='FAIL')])
    assert summary['accepted']['groups'] == []
    assert summary['unattempted']['candidate_count'] == 1
    groups = summary['rejected']['groups']
    assert len(groups) == 4
    assert sum(g['operation_count'] for g in groups) == 5
    group = next(g for g in groups if g['region']=='aca' and g['measurement_method']=='local_baseline_diameter')
    assert group['parameters']['severity_percent']['empirical_values'] == [{'value':40,'count':2}]


def test_malformed_candidates_and_missing_numeric_values_remain_reportable():
    candidates = [None, [], ['bad', {'type':[]}], [{'center_mm':3}, {'center_mm':'invalid'}, {'enabled':True}]]
    summary = parameter_distribution(candidates, [])['candidate_pool']
    assert summary['candidate_count'] == 4
    assert summary['malformed_entry_count'] == 3
    assert summary['baseline_candidate_count'] == 1
    group = summary['groups'][0]
    assert group['operation_count'] == 3
    assert group['parameters']['center_mm']['missing_count'] == 2
    assert 'enabled' not in group['parameters']


def test_pairs_reveal_filter_shift_hidden_by_identical_marginals():
    def operation(length, severity):
        return dict(region='aca', measurement_method='local_baseline_area',
                    length_mm=length, severity_percent=severity)
    candidates = [[operation(2,20)], [operation(4,40)],
                  [operation(2,40)], [operation(4,20)]]
    attempts = [dict(parameters=c, status='PASS' if i<2 else 'FAIL')
                for i,c in enumerate(candidates)]
    summary = parameter_distribution(candidates, attempts)
    accepted, rejected = [summary[k]['groups'][0] for k in ('accepted','rejected')]
    assert accepted['parameters'] == rejected['parameters']
    assert accepted['parameter_pairs'][0]['empirical_values'] == [
        {'values':[2,20], 'count':1}, {'values':[4,40], 'count':1}]
    assert rejected['parameter_pairs'][0]['empirical_values'] == [
        {'values':[2,40], 'count':1}, {'values':[4,20], 'count':1}]


def test_pairs_count_only_complete_finite_rows_without_imputation():
    rows = [{'a':1,'b':2}, {'a':1,'b':2}, {'a':3},
            {'a':True,'b':4}, {'a':float('nan'),'b':5}, {'a':6,'b':float('inf')}]
    result = parameter_distribution([rows], [])['candidate_pool']['groups'][0]
    assert result['parameter_pairs'] == [{
        'fields':['a','b'], 'count':2, 'missing_count':4,
        'empirical_values':[{'values':[1,2], 'count':2}]}]
