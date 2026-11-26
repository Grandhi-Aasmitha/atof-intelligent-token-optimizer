"""Offline positive and negative fixtures for every structured transformation."""
from .structured import StructuredRequest,optimize_structured,FEATURE_BY_KIND,STRUCTURED_FEATURES

def fixtures():
    common=[{"id":"keep","text":"Required evidence "+("important facts "*20)},
            {"id":"drop","text":"Optional duplicate or stale material "+("irrelevant words "*150),"optional":True,"score":0}]
    pair=[{"id":"a","text":"Repeat this exact long input "*100},
          {"id":"b","text":"Repeat this exact long input "*100,"optional":True}]
    history=[{"id":"old","text":"Superseded exchange "*150,"optional":True,"superseded_by":"new"},
             {"id":"new","text":"Current verified exchange"}]
    return [
        ("core.prompt",dict(kind="prompt_parts",items=pair,allow_deduplication=True)),
        ("core.conversation_history",dict(kind="history",items=history,allow_pruning=True)),
        ("core.memory",dict(kind="memory",items=common,min_score=.5,allow_pruning=True)),
        ("core.rag_retrieval",dict(kind="retrieval",items=common,top_k=1,allow_pruning=True)),
        ("agent.handoff",dict(kind="handoff",items=common,allowed_ids=["keep"],allow_pruning=True)),
        ("agent.state",dict(kind="state",items=common,allowed_ids=["keep"],allow_pruning=True)),
        ("agent.tool_schema",dict(kind="tool_schema",items=common,allowed_ids=["keep"],allow_pruning=True)),
        ("advanced.tool_search",dict(kind="tool_search",items=common,top_k=1,allow_pruning=True)),
        ("enterprise.embedding",dict(kind="embedding",items=pair,allow_deduplication=True)),
        ("enterprise.duplicate_request",dict(kind="duplicate_requests",items=pair,allow_deduplication=True,idempotent_batch=True)),
        ("core.token_budget",dict(kind="state",items=common,token_budget=100,allow_pruning=True)),
        ("advanced.compaction",dict(kind="history",items=history,compaction_trigger=64,allow_pruning=True)),
    ]

def verify():
    rows=[]
    for feature,kwargs in fixtures():
        req=StructuredRequest(task="Explain required evidence",authorized=True,**kwargs)
        on=optimize_structured(req,persist=False,diagnostic=True)
        off=optimize_structured(req.model_copy(update={"optimization_enabled":False}),persist=False,diagnostic=True)
        passed=(on["report"]["executed_features"]==[feature] and on["after"]<on["before"] and
                not off["report"]["executed_features"] and off["before"]==off["after"]==on["before"] and
                off["items"]==[x.model_dump() for x in req.items] and on["task"]==req.task)
        rows.append({"feature":feature,"passed":passed,"before":on["before"],"after":on["after"]})
    return {"passed":sum(x["passed"] for x in rows),"total":len(rows),"results":rows,"provider_savings_verified":False}

if __name__=="__main__":
    import json
    result=verify()
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["passed"]==result["total"] else 1)
