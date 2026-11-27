'use strict';

// Only an explicitly selected editor fragment is authorized. Do not read the
// rest of the file, other files, terminal history or private agent state.
function evidenceSlot(text) {
  if (/^diff --git /m.test(text) && /^@@ /m.test(text)) return 'diff';
  if (/\b(?:PASSED|FAILED)\b/.test(text) && /(?:^|\n)\s*(?:test_[^\n]+|Tests run:)/m.test(text)) return 'test_output';
  if (/Traceback \(most recent call last\)|(?:^|\n)\s*[\w.]+(?:Error|Exception):/.test(text)) return 'error_output';
  return 'context';
}
function buildRequest(task, text, tokenBudget=1600) {
  if (typeof task !== 'string' || !task.trim() || Array.from(task).length > 20000) throw Error('Enter a task of at most 20,000 characters');
  if (typeof text !== 'string' || Array.from(text).length > 300000) throw Error('Selection exceeds 300,000 characters');
  return {task, ...(text ? {[evidenceSlot(text)]:text}:{}), token_budget:tokenBudget};
}
function acceptPrepared(result, task, text) {
  if (!result || result.adapter_id !== 'vscode_copilot_model' || typeof result.prompt !== 'string' ||
      result.report?.agent !== 'copilot' || result.report?.delivery_status !== 'owned_payload_prepared') throw Error('Invalid preparation response');
  const prompt = JSON.parse(result.prompt);
  if (!prompt || Object.keys(prompt).length !== 2 || prompt.task !== task || typeof prompt.evidence !== 'string') throw Error('Task or input framing changed');
  const before=result.original_prompt_estimate, after=result.prepared_prompt_estimate;
  if (!Number.isSafeInteger(before)||!Number.isSafeInteger(after)||before<0||after<0||after>before||
      result.prompt_estimated_reduction!==before-after) throw Error('Invalid token estimates');
  if (prompt.evidence !== text && (result.report.control_policy !== 'enabled' ||
      result.report.fidelity_status !== 'passed'||after>=before||!result.report.executed_features?.length)) throw Error('Unverified reduction');
  if (after===before && prompt.evidence!==text) throw Error('Original evidence changed without reduction');
  return result.prompt;
}
async function sendOne(model, message, token) {
  if (token?.isCancellationRequested) return null;
  const reply=await model.sendRequest([message],{},token);
  let text='';
  for await (const fragment of reply.text) {
    if (token?.isCancellationRequested) return null;
    text+=fragment;
    if (text.length>2000000) throw Error('Model response exceeded display limit');
  }
  return text;
}
// Count the complete explicit user message using the selected model's tokenizer.
// This is a model-reported count of the message, not billed/provider usage.
async function compareInput(model, makeMessage, task, original, prepared, token) {
  if(typeof model.countTokens!=='function'||token?.isCancellationRequested)return null;
  try {
    const before=await model.countTokens(makeMessage(JSON.stringify({task,evidence:original})),token);
    const after=await model.countTokens(makeMessage(prepared),token);
    if(token?.isCancellationRequested||![before,after].every(v=>Number.isSafeInteger(v)&&v>=0))return null;
    return {before,after,difference:before-after};
  } catch (_) { return null; }
}
module.exports={evidenceSlot,buildRequest,acceptPrepared,sendOne,compareInput};
