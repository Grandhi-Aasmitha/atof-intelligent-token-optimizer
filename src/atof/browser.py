"""Opt-in browser-owned single-turn requests. No native web chat access."""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.request import Request, HTTPRedirectHandler, build_opener
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .adapters import AgentAdapter
from .models import OptimizeRequest

Provider = Literal["openai", "gemini"]
CONFIG = {
    "openai": ("OPENAI_API_KEY", "ATOF_BROWSER_OPENAI_MODEL", "browser_openai"),
    "gemini": ("GEMINI_API_KEY", "ATOF_BROWSER_GEMINI_MODEL", "browser_gemini"),
}
MODEL_PATTERN = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}\Z")


class BrowserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Provider
    task: str = Field(min_length=1, max_length=20000)
    evidence: str = Field(default="", max_length=300000)
    consent: StrictBool

    def optimization_request(self):
        text = self.evidence
        slot = "context"
        if re.search(r"^diff --git ", text, re.M) and re.search(r"^@@ ", text, re.M):
            slot = "diff"
        elif re.search(r"\b(?:PASSED|FAILED)\b", text) and re.search(r"^\s*(?:test_|Tests run:)", text, re.M):
            slot = "test_output"
        elif re.search(r"Traceback \(most recent call last\)|^\s*[\w.]+(?:Error|Exception):", text, re.M):
            slot = "error_output"
        return OptimizeRequest(task=self.task, **({slot: text} if text else {}))


@dataclass(frozen=True)
class ApprovedProvider:
    provider: str
    model: str
    adapter_id: str
    key: str = field(repr=False)


def configured(provider):
    if os.getenv("ATOF_BROWSER_API_ENABLED") != "1" or provider not in CONFIG:
        return None
    key_name, model_name, adapter = CONFIG[provider]
    model, key = os.getenv(model_name, ""), os.getenv(key_name, "")
    if not key.strip() or not MODEL_PATTERN.fullmatch(model) or ".." in model:
        return None
    return ApprovedProvider(provider, model, adapter, key)


def status():
    providers = []
    for provider in CONFIG:
        item = configured(provider)
        if item:
            providers.append({"provider":item.provider, "model":item.model})
    return {"enabled":os.getenv("ATOF_BROWSER_API_ENABLED")=="1",
            "providers":providers, "native_web_chat_connected":False,
            "provider_savings_verified":False}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def provider_request(item, prompt):
    if item.provider == "openai":
        return ("https://api.openai.com/v1/responses",
                {"model":item.model,"input":prompt,"store":False,"max_output_tokens":2048},
                {"Authorization":"Bearer "+item.key})
    if item.provider == "gemini":
        return ("https://generativelanguage.googleapis.com/v1beta/models/"+item.model+":generateContent",
                {"contents":[{"role":"user","parts":[{"text":prompt}]}],
                 "generationConfig":{"maxOutputTokens":2048}},
                {"x-goog-api-key":item.key})
    raise ValueError("Unsupported provider")


def _post(url, body, headers):
    """Fixed provider destination, no redirect and no application retry."""
    req = Request(url, data=json.dumps(body).encode("utf-8"),
                  headers={"Content-Type":"application/json",**headers}, method="POST")
    with build_opener(NoRedirect()).open(req, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError("Unexpected provider response")
        raw = response.read(4_000_001)
    if len(raw)>4_000_000:
        raise RuntimeError("Provider response exceeds limit")
    return json.loads(raw)


def extract_answer(provider, result):
    if provider == "openai":
        if result.get("status") != "completed":
            raise RuntimeError("Incomplete response")
        answer = "\n".join(c.get("text","") for item in result.get("output",[])
                           if item.get("type")=="message"
                           for c in item.get("content",[]) if c.get("type")=="output_text")
    else:
        candidate = result["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise RuntimeError("Incomplete response")
        answer = "\n".join(p["text"] for p in candidate["content"]["parts"]
                           if "text" in p and not p.get("thought",False))
    if not answer.strip() or len(answer)>2_000_000:
        raise RuntimeError("Invalid text response")
    return answer


def ask(payload: BrowserRequest):
    if not payload.consent:
        raise PermissionError("Explicit paid request consent required")
    if not payload.task.strip():
        raise ValueError("Task required")
    item = configured(payload.provider)
    if item is None:
        raise PermissionError("Browser provider not enabled or configured")

    def sender(prompt):
        url, body, headers = provider_request(item,prompt)
        return extract_answer(item.provider,_post(url,body,headers))

    # dispatch applies global policy, validates candidate and calls sender once.
    # It records metadata only; failure clears reduction and never retries.
    result = AgentAdapter(item.adapter_id).dispatch(payload.optimization_request(),sender,authorized=True)
    return {"answer":result["answer"], "report":result["report"],
            "original_prompt_estimate":result.get("original_prompt_estimate"),
            "prepared_prompt_estimate":result.get("prepared_prompt_estimate"),
            "provider_savings_verified":False, "model_consumption_verified":False,
            "sender_returned":result.get("sender_returned",False)}
