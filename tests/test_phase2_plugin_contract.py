import pytest
from atof.engines.registry import EngineRegistry
from atof.engines.base import PluginSpec
from atof.models import OptimizeRequest
from atof.analyzer import analyze
from atof.planner import select
from atof.registry import FeatureRegistry


class Plugin:
    def __init__(self, ident, priority, depends=(), conflicts=(), evidence="context"):
        self.feature_id = ident
        self.spec = PluginSpec(ident, evidence, priority, conflicts=conflicts,
                               depends_on=depends, validator=lambda original, candidate: True)


def test_dependency_order_and_missing_dependency():
    engines=EngineRegistry([Plugin("dependent",100,depends=("dependency",),evidence="tool_output"),
                            Plugin("dependency",1)])
    assert [s.feature_id for s in engines.strategies()]==["dependency","dependent"]
    request=OptimizeRequest(task="Explain",context="source",tool_output="result")
    decisions=select(request,analyze(request),FeatureRegistry(),engines)
    assert [d.feature_id for d in decisions if d.status=="selected"]==["dependency","dependent"]
    engines=EngineRegistry([Plugin("dependent",100,depends=("missing",))])
    decisions=select(request,analyze(request),FeatureRegistry(),engines)
    assert decisions[0].reason=="missing_strategy_dependency"


def test_cycle_rejected():
    with pytest.raises(ValueError,match="cyclic optimizer"):
        EngineRegistry([Plugin("a",10,depends=("b",)),Plugin("b",1,depends=("a",))])


def test_conflict_is_symmetric():
    engines=EngineRegistry([Plugin("a",10,conflicts=("b",)),Plugin("b",1,evidence="tool_output")])
    request=OptimizeRequest(task="Explain",context="source",tool_output="result")
    decisions=select(request,analyze(request),FeatureRegistry(),engines)
    assert [d.status for d in decisions]==["selected","skipped"]
