'use strict';
const $=id=>document.getElementById(id);
let busy=false, available=false;
function enable(){
 for(const id of ['provider','task','context','consent','send'])$(id).disabled=busy||!available;
}
async function config(){
 try{
  const response=await fetch('/v1/browser/status',{cache:'no-store'});
  if(!response.ok)throw Error('Unavailable');
  const state=await response.json();
  $('provider').replaceChildren();
  for(const p of state.providers){
   const option=document.createElement('option');option.value=p.provider;
   option.textContent=(p.provider==='openai'?'OpenAI API':'Gemini API')+' — '+p.model;
   $('provider').append(option);
  }
  available=state.enabled&&state.providers.length>0;
  $('status').textContent=available?'Approved API client configured. Shared ATOF ON/OFF policy applies.':'Browser AI client disabled or no approved model configured. See Phase 9 setup guide.';
 }catch(_){available=false;$('status').textContent='Local service unavailable.'}
 enable();
}
$('ask').addEventListener('submit',async event=>{
 event.preventDefault();
 if(busy||!available||!$('consent').checked||!$('task').value.trim())return;
 const payload={provider:$('provider').value,task:$('task').value,evidence:$('context').value,consent:true};
 busy=true;enable();$('answer').textContent='Request submitted…';$('report').textContent='';
 try{
  const response=await fetch('/v1/browser/ask',{method:'POST',cache:'no-store',
   headers:{'Content-Type':'application/json','X-ATOF-Browser':'1'},body:JSON.stringify(payload)});
  if(!response.ok)throw Error('Request rejected');
  const data=await response.json();
  if(!data.sender_returned||typeof data.answer!=='string')throw Error('Submission not confirmed');
  $('answer').textContent=data.answer;
  $('report').textContent='Prepared input estimates: '+data.original_prompt_estimate+' → '+data.prepared_prompt_estimate+
   ' tokens. Actual provider savings remain unverified.';
 }catch(_){$('answer').textContent='Request not confirmed. No automatic retry. Check approved API access and the local report before retrying.'}
 finally{busy=false;$('consent').checked=false;enable();}
});
config();
