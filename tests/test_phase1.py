from fastapi.testclient import TestClient
from atof.api import app
from atof.models import OptimizeRequest
from atof.registry import FeatureRegistry
from atof.service import optimize

client=TestClient(app)
SOURCE='def subtotal(items):\n    return sum(items)\n\ndef total(items):\n    return subtotal(items)\n\ndef unrelated_0(): return 0\ndef unrelated_1(): return 1\ndef unrelated_2(): return 2\ndef unrelated_3(): return 3\ndef unrelated_4(): return 4\ndef unrelated_5(): return 5\ndef unrelated_6(): return 6\ndef unrelated_7(): return 7\ndef unrelated_8(): return 8\ndef unrelated_9(): return 9\ndef unrelated_10(): return 10\ndef unrelated_11(): return 11\ndef unrelated_12(): return 12\ndef unrelated_13(): return 13\ndef unrelated_14(): return 14\ndef unrelated_15(): return 15\ndef unrelated_16(): return 16\ndef unrelated_17(): return 17\ndef unrelated_18(): return 18\ndef unrelated_19(): return 19\ndef unrelated_20(): return 20\ndef unrelated_21(): return 21\ndef unrelated_22(): return 22\ndef unrelated_23(): return 23\ndef unrelated_24(): return 24\ndef unrelated_25(): return 25\ndef unrelated_26(): return 26\ndef unrelated_27(): return 27\ndef unrelated_28(): return 28\ndef unrelated_29(): return 29\ndef unrelated_30(): return 30\ndef unrelated_31(): return 31\ndef unrelated_32(): return 32\ndef unrelated_33(): return 33\ndef unrelated_34(): return 34\ndef unrelated_35(): return 35\ndef unrelated_36(): return 36\ndef unrelated_37(): return 37\ndef unrelated_38(): return 38\ndef unrelated_39(): return 39\ndef unrelated_40(): return 40\ndef unrelated_41(): return 41\ndef unrelated_42(): return 42\ndef unrelated_43(): return 43\ndef unrelated_44(): return 44\ndef unrelated_45(): return 45\ndef unrelated_46(): return 46\ndef unrelated_47(): return 47\ndef unrelated_48(): return 48\ndef unrelated_49(): return 49\ndef unrelated_50(): return 50\ndef unrelated_51(): return 51\ndef unrelated_52(): return 52\ndef unrelated_53(): return 53\ndef unrelated_54(): return 54\ndef unrelated_55(): return 55\ndef unrelated_56(): return 56\ndef unrelated_57(): return 57\ndef unrelated_58(): return 58\ndef unrelated_59(): return 59\ndef unrelated_60(): return 60\ndef unrelated_61(): return 61\ndef unrelated_62(): return 62\ndef unrelated_63(): return 63\ndef unrelated_64(): return 64\ndef unrelated_65(): return 65\ndef unrelated_66(): return 66\ndef unrelated_67(): return 67\ndef unrelated_68(): return 68\ndef unrelated_69(): return 69\ndef unrelated_70(): return 70\ndef unrelated_71(): return 71\ndef unrelated_72(): return 72\ndef unrelated_73(): return 73\ndef unrelated_74(): return 74\ndef unrelated_75(): return 75\ndef unrelated_76(): return 76\ndef unrelated_77(): return 77\ndef unrelated_78(): return 78\ndef unrelated_79(): return 79\ndef unrelated_80(): return 80\ndef unrelated_81(): return 81\ndef unrelated_82(): return 82\ndef unrelated_83(): return 83\ndef unrelated_84(): return 84\ndef unrelated_85(): return 85\ndef unrelated_86(): return 86\ndef unrelated_87(): return 87\ndef unrelated_88(): return 88\ndef unrelated_89(): return 89'

def request(**overrides):
    data={'task':'Explain total and dependencies','files':[{'path':'service.py','content':SOURCE}],'agent':'custom_api'}
    data.update(overrides)
    return OptimizeRequest.model_validate(data)

def test_registry_exactly_48_unique():
    reg=FeatureRegistry();assert len(reg.all())==48;assert len({f.id for f in reg.all()})==48
    assert sum(f.implemented for f in reg.all())==1

def test_dynamic_selection_only_relevant():
    result=optimize(request(execute=False))
    assert [x.feature_id for x in result.report.decisions]==['coding.code_context']
    assert result.report.decisions[0].status=='applicable'

def test_code_context_actual_engine():
    result=optimize(request())
    assert result.optimized_context
    assert 'def total' in result.optimized_context
    assert 'def subtotal' in result.optimized_context
    assert 'unrelated_89' not in result.optimized_context
    assert result.report.estimated_reduction_tokens>0
    assert result.report.delivery_status=='payload_returned_to_client'
    assert result.report.provider_tokens_saved is None

def test_copilot_reports_unsupported_not_success():
    result=optimize(request(agent='copilot'))
    assert result.optimized_context is None
    assert result.report.decisions[0].status=='unsupported'

def test_empty_files_only_no_optimization():
    result=optimize(OptimizeRequest(task='Hello, what is a token?'))
    assert result.report.decisions==[]
    assert result.optimized_context is None

def test_api_contract():
    assert client.get('/health').json()['status']=='ok'
    assert client.get('/v1/features').json()['count']==48
    response=client.post('/v1/optimize',json=request().model_dump())
    assert response.status_code==200
    assert response.json()['optimized_context']

def test_duplicate_file_paths_rejected():
    response=client.post('/v1/optimize',json={'task':'Explain function','files':[{'path':'a.py','content':'pass'},{'path':'a.py','content':'pass'}]})
    assert response.status_code==422

def test_diff_not_falsely_executed():
    result=optimize(OptimizeRequest(task='Review this diff\ndiff --git a/a.py b/a.py'))
    assert result.report.decisions[0].feature_id=='coding.code_diff'
    assert result.report.decisions[0].status=='unsupported'
