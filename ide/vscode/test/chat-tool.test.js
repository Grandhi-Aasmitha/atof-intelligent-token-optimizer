'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const {sourcePath,readContext}=require('../chat-tool');
test('reject traversal and sensitive paths',()=>{
  for(const p of ['../a.py','.env','secrets/a.py','credentials.py','node_modules/a.js','C:\\a.py','/a.py'])assert.throws(()=>sourcePath('/tmp/project',p));
});
test('OFF avoids source and optimization calls; ON returns only accepted evidence',async()=>{
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'atof-chat-'));
  try{
    await fs.writeFile(path.join(root,'cart.py'),'def total(): return 100\n');
    let enabled=false,calls=0;
    const args={input:{task:'Explain total',path:'cart.py'},trusted:()=>true,roots:()=>[root],budget:1600,api:async(route,method,payload)=>{
      if(route==='/v1/control')return {available:true,settings:{enabled}};
      calls++;assert.equal(payload.files[0].content,'def total(): return 100\n');
      return {optimized_context:'def total(): return 100',report:{agent:'copilot',execution_transport:'vscode_chat_tool',control_policy:'enabled',fidelity_status:'passed',estimated_reduction_tokens:1,executed_features:['test-fixture']}};
    }};
    assert.match(await readContext(args),/OFF/);assert.equal(calls,0);
    enabled=true;assert.equal(await readContext(args),'def total(): return 100');assert.equal(calls,1);
    args.trusted=()=>false;assert.match(await readContext(args),/unavailable/);assert.equal(calls,1);
  }finally{await fs.rm(root,{recursive:true,force:true});}
});
