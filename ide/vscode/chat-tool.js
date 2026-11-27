'use strict';
const fs=require('node:fs/promises');
const path=require('node:path');
const TOOL_NAME='atof_read_context';
const LIMIT=300000;
const extensions=new Set(['.py','.js','.ts','.jsx','.tsx','.java','.kt','.go','.rs','.cs','.html','.css','.sql','.rb','.php','.c','.cpp','.h','.vue']);
function sourcePath(root,relative,kind='source'){
  if(typeof relative!=='string'||!relative||relative.length>1024||path.isAbsolute(relative)||/[:\x00-\x1f]/.test(relative))throw Error('Invalid path');
  const parts=relative.split(/[\\/]/);
  if(parts.some(p=>!p||p==='..'||p==='.'||p.startsWith('.')||/^(node_modules|vendor|dist|build|target|secrets?|credentials?|private|__pycache__)$/i.test(p)||/secret|credential|password|token|private[_-]?key|^config[._-]|^settings[._-]/i.test(p)))throw Error('Restricted path');
  if(!(kind==='source'?extensions:new Set(kind==='diff'?['.diff','.patch']:['.log','.txt'])).has(path.extname(relative).toLowerCase()))throw Error('Unsupported source extension');
  return path.join(root,...parts);
}
function inside(root,target){
  const rel=path.relative(root,target);
  return !!rel&&!path.isAbsolute(rel)&&rel!=='..'&&!rel.startsWith('..'+path.sep);
}
async function readContext({input,token,api,budget,trusted,roots}){
  const bypass='ATOF unavailable or not applicable; use normal authorized source tools if needed.';
  const disabled='ATOF is OFF; use normal authorized source tools.';
  try{
    if(token?.isCancellationRequested||!trusted())return bypass;
    const folders=roots();
    if(folders.length!==1||typeof input?.task!=='string'||!input.task.trim()||input.task.length>20000)return bypass;
    const state=await api('/v1/control');
    if(!state.available)return bypass;
    if(!state.settings.enabled)return disabled;
    const root=await fs.realpath(folders[0]);
    const kind=input.kind||'source';
    if(!['source','error_output','test_output','diff'].includes(kind))return bypass;
    const paths=input.paths??(input.path?[input.path]:[]);
    if(!Array.isArray(paths)||paths.length<1||paths.length>8||new Set(paths).size!==paths.length|| (kind!=='source'&&paths.length!==1))return bypass;
    const files=[];let total=0;
    for(const relative of paths){
    if(token?.isCancellationRequested||!trusted())return bypass;
    const candidate=sourcePath(root,relative,kind);
    const actual=await fs.realpath(candidate);
    if(!inside(root,actual)||path.relative(candidate,actual)!=='')return bypass;
    const stat=await fs.stat(actual);
    if(!stat.isFile()||stat.size>LIMIT)return bypass;
    const handle=await fs.open(actual,'r');
    let raw;
    try{
      const check=await handle.stat();
      if(!check.isFile()||check.size>LIMIT)return bypass;
      const bytes=Buffer.alloc(LIMIT+1);
      let offset=0;
      while(offset<bytes.length){
        const {bytesRead}=await handle.read(bytes,offset,bytes.length-offset,null);
        if(!bytesRead)break;
        offset+=bytesRead;
      }
      if(offset>LIMIT)return bypass;
      raw=new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,offset));
    }finally{await handle.close();}
    if(!raw.trim()||raw.includes('\0')||token?.isCancellationRequested||!trusted())return bypass;
    total+=Buffer.byteLength(raw);if(total>LIMIT)return bypass;
    files.push({path:relative.replace(/\\/g,'/'),content:raw});
    }
    const evidence=kind==='source'?{files}:{[kind]:files[0].content};
    const result=await api('/v1/integrations/vscode-chat/optimize','POST',{task:input.task,...evidence,token_budget:budget},{'X-ATOF-Adapter':'1'});
    if(token?.isCancellationRequested||!trusted())return bypass;
    const report=result?.report;
    if(!report||report.agent!=='copilot'||report.execution_transport!=='vscode_chat_tool')return bypass;
    if(report.control_policy!=='enabled')return report.control_policy==='disabled'?disabled:bypass;
    const accepted=Boolean(result.optimized_context&&report.fidelity_status==='passed'&&report.estimated_reduction_tokens>0&&report.executed_features?.length);
    if(accepted){
      const latest=await api('/v1/control');if(!latest.available||!latest.settings.enabled)return disabled;
      try{await api('/v1/integrations/vscode-native/receipt','POST',{request_id:report.request_id},{'X-ATOF-Adapter':'1'});}catch(_){}
      if(token?.isCancellationRequested||!trusted())return bypass;
      return result.optimized_context;
    }
    return files.map(f=>'# '+f.path+'\n'+f.content).join('\n\n');
  }catch(_){return bypass;}
}
module.exports={TOOL_NAME,sourcePath,inside,readContext};
