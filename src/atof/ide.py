"""Explicit selected-text optimization, not automatic assistant interception."""
from typing import Literal
from pydantic import BaseModel, Field
from .models import OptimizeRequest, OptimizeResponse
from .service import optimize

class IDERequest(BaseModel):
    ide: Literal['vscode','intellij','eclipse']
    task: str = Field(min_length=1,max_length=20000)
    text: str = Field(min_length=1,max_length=300000)
    path_label: str = Field(default='selection.txt',max_length=1024)
    evidence_kind: Literal['source','error','test','diff'] = 'source'
    token_budget: int = Field(default=1600,ge=64,le=200000)
    execute: bool = True

def optimize_selection(request: IDERequest) -> OptimizeResponse:
    args=dict(task=request.task,agent='custom_api',token_budget=request.token_budget,execute=request.execute)
    if request.evidence_kind=='source':
        args['files']=[{'path':request.path_label,'content':request.text}]
    else:
        args[{'error':'error_output','test':'test_output','diff':'diff'}[request.evidence_kind]]=request.text
    response=optimize(OptimizeRequest(**args))
    response.report.warnings.append('Explicit IDE candidate only: not automatically sent to any AI model')
    return response
