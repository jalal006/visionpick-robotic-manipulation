"""Regression checks against recorded real integration evidence, no simulator needed."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workcell_logic import summarize_report


@pytest.fixture
def report():
    return json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/milestone02-results.json').read_text())


def test_recorded_integration_report_has_complete_acceptance_evidence(report):
    summary = summarize_report(report)
    assert summary['executions'] == 3
    assert summary['worst_joint_error'] <= .02


@pytest.mark.parametrize('tamper', ['missing_geometry','valid_blocked','invalid_control',
    'no_contacts','executed_control','missing_home','stale_feedback','joint_error','contact'])
def test_incomplete_or_failed_evidence_cannot_pass(report, tamper):
    rows = report['events']
    negative = next(r for r in rows if r['event'] == 'negative_test')
    executed = next(r for r in rows if r['event'] == 'executed')
    if tamper == 'missing_geometry':
        report['events'] = [r for r in rows if r['event'] != 'gazebo_geometry']
    elif tamper == 'valid_blocked': negative['with_fixture']['valid'] = True
    elif tamper == 'invalid_control': negative['without_fixture']['valid'] = False
    elif tamper == 'no_contacts': negative['with_fixture']['contacts'] = []
    elif tamper == 'executed_control': negative['control_plan_executed'] = True
    elif tamper == 'missing_home':
        report['events'] = [r for r in rows if not (r['event'] == 'executed' and r['label'] == 'home')]
    elif tamper == 'stale_feedback': executed['feedback_samples'] = 0
    elif tamper == 'joint_error': executed['max_error'] = .03
    elif tamper == 'contact': executed['robot_workcell_contacts'] = 1
    with pytest.raises(ValueError): summarize_report(report)
