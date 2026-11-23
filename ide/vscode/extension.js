'use strict';
const vscode=require('vscode');
const http=require('http');
function api(){
  const raw=vscode.workspace.getConfiguration('atof').get('apiUrl','http://127.0.0.1:8080');
  const url=new URL(raw);
  if(url.protocol!=='http:'||!['127.0.0.1','localhost','[::1]'].includes(url.hostname))
    throw Error('ATOF supports loopback HTTP only');
  url.pathname='/v1/ide/optimize';
  return url;
}
function send(url,payload){
  return new Promise((resolve,reject)=>{
    const body=JSON.stringify(payload);
    const req=http.request(url,{method:'POST',timeout:12000,headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body)}},res=>{
      let result='';
      res.setEncoding('utf8');
      res.on('data',part=>{result+=part;if(result.length>4000000)req.destroy(Error('Response too large'));});
      res.on('end',()=>{try{if(res.statusCode!==200)throw Error('API returned '+res.statusCode);resolve(JSON.parse(result));}catch(e){reject(e)}});
    });
    req.on('timeout',()=>req.destroy(Error('Local ATOF timed out')));
    req.on('error',reject);
    req.end(body);
  });
}
async function optimize(){
  try{
    const editor=vscode.window.activeTextEditor;
    if(!editor||editor.selection.isEmpty){vscode.window.showInformationMessage('Select text first');return;}
    const content=editor.document.getText(editor.selection);
    const kind=await vscode.window.showQuickPick([{label:'Source',value:'source'},{label:'Error',value:'error'},
      {label:'Test output',value:'test'},{label:'Diff',value:'diff'}],{placeHolder:'Evidence type'});
    if(!kind)return;
    const task=await vscode.window.showInputBox({prompt:'ATOF task',value:'Explain and retain relevant evidence'});
    if(!task)return;
    const confirm=await vscode.window.showWarningMessage('Send '+content.length+' characters to local ATOF?',{modal:true},'Optimize');
    if(confirm!=='Optimize')return;
    const r=await send(api(),{ide:'vscode',task,text:content,evidence_kind:kind.value,
      path_label:editor.document.fileName.split(/[\\/]/).pop()||'selection.txt',
      token_budget:vscode.workspace.getConfiguration('atof').get('tokenBudget',1600)});
    const x=r.report;
    const report='ATOF candidate — not automatically sent to AI\nEstimated tokens before: '+x.original_estimated_tokens+
      '\nAfter: '+x.optimized_estimated_tokens+'\nRemoved: '+x.estimated_reduction_tokens+
      '\nFeatures: '+x.executed_features.join(', ')+'\nProvider token savings: UNVERIFIED\n\n';
    const doc=await vscode.workspace.openTextDocument({language:'plaintext',content:report+(r.optimized_context||'[No safe reduction]')});
    await vscode.window.showTextDocument(doc,{preview:false});
  }catch(e){vscode.window.showErrorMessage('ATOF: '+e.message);}
}
async function dashboard(){try{const u=api();u.pathname='/dashboard';await vscode.env.openExternal(vscode.Uri.parse(u.toString()));}
  catch(e){vscode.window.showErrorMessage('ATOF: '+e.message);}}
function activate(ctx){ctx.subscriptions.push(vscode.commands.registerCommand('atof.optimizeSelection',optimize));
ctx.subscriptions.push(vscode.commands.registerCommand('atof.openDashboard',dashboard));}
function deactivate(){}
module.exports={activate,deactivate};
