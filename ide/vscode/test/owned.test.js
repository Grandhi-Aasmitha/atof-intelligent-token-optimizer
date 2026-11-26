'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {buildRequest,evidenceSlot,acceptPrepared,sendOne}=require('../owned');
const {localOrigin}=require('../client');
const task='Diagnose error', raw='heartbeat ok\n'.repeat(150)+'RuntimeError: fail';
function prepared(evidence=raw, after=700, policy='disabled'){
 return {adapter_id:'vscode_copilot_model',prompt:JSON.stringify({task,evidence}),
 original_prompt_estimate:700,prepared_prompt_estimate:after,prompt_estimated_reduction:700-after,
 report:{agent:'copilot',delivery_status:'owned_payload_prepared',control_policy:policy,fidelity_status:'passed',executed_features:after<700?['coding.error_context']:[]}};
}
test('evidence classification and unchanged task',()=>{
 assert.equal(buildRequest(task,raw).error_output,raw);
 assert.equal(evidenceSlot('diff --git a/a b/a\n@@ -1 +1 @@\n-old\n+new'),'diff');
 assert.equal(evidenceSlot('test_ok PASSED\ntest_bad FAILED'),'test_output');
 assert.equal(evidenceSlot('arbitrary text'),'context');
 assert.deepEqual(buildRequest('What is Python?',''),{task:'What is Python?',token_budget:1600});
});
test('original and reduced input, reject task edits and disabled reduction',()=>{
 assert.equal(JSON.parse(acceptPrepared(prepared(),task,raw)).evidence,raw);
 const reduced='RuntimeError: fail';
 assert.equal(JSON.parse(acceptPrepared(prepared(reduced,50,'enabled'),task,raw)).evidence,reduced);
 assert.throws(()=>acceptPrepared(prepared(reduced,50,'disabled'),task,raw));
 assert.throws(()=>acceptPrepared(prepared(),task+' changed',raw));
 assert.throws(()=>acceptPrepared({...prepared(),adapter_id:'chatgpt_web'},task,raw));
});
test('only one message and no retry',async()=>{
 let calls=0;
 const message={content:'prepared only'};
 const model={sendRequest:async(messages)=>{calls++;assert.deepEqual(messages,[message]);return {text:(async function*(){yield 'a';yield 'b';})()}}};
 assert.equal(await sendOne(model,message,{isCancellationRequested:false}),'ab');
 assert.equal(await sendOne(model,message,{isCancellationRequested:true}),null);
 assert.equal(calls,1);
 await assert.rejects(sendOne({sendRequest:async()=>{calls++;throw Error('fail')}},message,{}));
 assert.equal(calls,2);
});
test('local origin policy',()=>{
 assert.equal(localOrigin('http://127.0.0.1:8081'),'http://127.0.0.1:8081');
 for(const u of ['https://localhost:8081','http://example.com','http://user@localhost','http://localhost/path','http://localhost/?x=1'])assert.throws(()=>localOrigin(u));
});
