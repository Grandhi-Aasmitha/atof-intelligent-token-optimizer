'use strict';
// Copilot userPromptSubmitted command hook; no permission changes, no prompt rewrite.
const {request}=require('./client');
async function main(){
 let raw='';for await(const chunk of process.stdin){raw+=chunk;if(raw.length>100000)return;}
 const event=JSON.parse(raw);const task=event.prompt;
 if(typeof task!=='string'||!task.trim()||task.length>20000)return;
 const base='http://127.0.0.1:8081';
 const state=await request(base,'/v1/control');
 if(!state.available||!state.settings.enabled)return;
 await request(base,'/v1/integrations/vscode-native/observe','POST',{task},{'X-ATOF-Adapter':'1'});
}
main().catch(()=>{}).finally(()=>process.stdout.write('{}'));
