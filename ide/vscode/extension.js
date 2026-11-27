'use strict';
const vscode=require('vscode');
const path=require('node:path');
const fs=require('node:fs');
const {localOrigin,request}=require('./client');
const {buildRequest,acceptPrepared,sendOne,compareInput}=require('./owned');
const {readContext,TOOL_NAME}=require('./chat-tool');
const config=()=>vscode.workspace.getConfiguration('atof');
const origin=()=>localOrigin(config().get('apiUrl','http://127.0.0.1:8081'));
const api=(route,method,payload,headers)=>request(origin(),route,method,payload,headers);
const budget=()=>config().get('tokenBudget',1600);
function trustedLocal() {
  if (!vscode.workspace.isTrusted || vscode.env.remoteName) throw Error('ATOF requires a trusted local VS Code workspace');
}
function safeError(message) { vscode.window.showErrorMessage('ATOF: '+message); }
async function dashboard() {
  try { await vscode.env.openExternal(vscode.Uri.parse(origin()+'/dashboard')); }
  catch (_) { safeError('Check the configured local service URL.'); }
}
async function controlStatus(status) {
  try {
    const c=await api('/v1/control');
    await vscode.commands.executeCommand('setContext','atof.optimizationEnabled',Boolean(c.available&&c.settings.enabled&&vscode.workspace.isTrusted&&!vscode.env.remoteName));
    status.text=c.available?'$(shield) ATOF '+(c.settings.enabled?'ON':'OFF'):'$(warning) ATOF unavailable';
    status.tooltip='Local policy; Copilot may choose ATOF source tool. Native prompt replacement and provider savings unverified.';
  } catch (_) {
    await vscode.commands.executeCommand('setContext','atof.optimizationEnabled',false);
    status.text='$(debug-disconnect) ATOF offline';
    status.tooltip='Start the local ATOF service; click to open Control Center.';
  }
}
async function toggle(status) {
  try {
    trustedLocal();
    const c=await api('/v1/control');
    if(!c.available) throw Error('Settings unavailable');
    const updated=await api('/v1/control/enabled','PUT',{enabled:!c.settings.enabled},{'X-ATOF-Control':'1'});
    if(!updated.available) throw Error('Change unconfirmed');
    await controlStatus(status);
    vscode.window.showInformationMessage('ATOF '+(updated.settings.enabled?'enabled':'disabled')+' for supported request paths.');
  } catch (_) { safeError('Could not change policy. Start ATOF and check the Control Center.'); }
}
async function askAI() {
  try {
    trustedLocal();
    if (!vscode.lm?.selectChatModels || !vscode.LanguageModelChatMessage) return safeError('Language Model API unavailable in this VS Code version.');
    const editor=vscode.window.activeTextEditor;
    const text=editor&&!editor.selection.isEmpty?editor.document.getText(editor.selection):'';
    const task=await vscode.window.showInputBox({prompt:'Ask AI with ATOF (single-turn request)',ignoreFocusOut:true});
    if (task===undefined || !task.trim()) return;
    const payload=buildRequest(task,text,budget());
    // Never select another provider silently; selection is user-initiated and may prompt for consent.
    const models=await vscode.lm.selectChatModels({vendor:'copilot'});
    if (!models.length) return safeError('No approved Copilot language model is available.');
    const picked=await vscode.window.showQuickPick(models.map(model=>({label:model.name||model.id,description:model.family,model})),{placeHolder:'Select an approved model'});
    if (!picked) return;
    const permission=await vscode.window.showWarningMessage(
      'Send this task and '+text.length+' selected characters to the local ATOF service, then to '+picked.label+'? Use only authorized content.',{modal:true},'Continue');
    if(permission!=='Continue') return;
    let prompt, requestId;
    try {
      const result=await api('/v1/adapters/vscode_copilot_model/prepare','POST',payload,{'X-ATOF-Adapter':'1'});
      prompt=acceptPrepared(result,task,text);
      requestId=result.report.request_id;
    } catch (_) {
      // Do not silently send raw context if the optimizer is unavailable.
      const bypass=await vscode.window.showWarningMessage('ATOF preparation unavailable. Send the original task and selection without optimization?',{modal:true},'Send original');
      if(bypass!=='Send original') return;
      prompt=JSON.stringify({task,evidence:text});
    }
    let answer, counts=null;
    const receipt=async outcome=>{if(requestId)try{await api('/v1/integrations/vscode-owned/receipt','POST',{request_id:requestId,outcome},{'X-ATOF-Adapter':'1'});}catch(_){/* advisory only; never retry a model call */}};
    try { answer=await vscode.window.withProgress({location:vscode.ProgressLocation.Notification,title:'ATOF — waiting for AI response',cancellable:true},async(_,token)=>{
      if (token.isCancellationRequested) return null;
      const makeMessage=value=>vscode.LanguageModelChatMessage.User(value);
      counts=await compareInput(picked.model,makeMessage,task,text,prompt,token);
      if(token.isCancellationRequested)return null;
      const message=makeMessage(prompt);
      // Exactly one extension-owned message and one sendRequest invocation.
      // No second original copy, no model retry, no hidden native-chat interception.
      return sendOne(picked.model,message,token);
    }); } catch(error) { await receipt('submission_unconfirmed'); throw error; }
    if(answer===null) { await receipt('submission_unconfirmed'); return; }
    await receipt('model_response_returned');
    const doc=await vscode.workspace.openTextDocument({language:'markdown',content:answer});
    await vscode.window.showTextDocument(doc,{preview:true});
    const measurement=counts?'Selected model user-message tokens: '+counts.before+' → '+counts.after+' (difference '+counts.difference+'). ':'Selected model token count unavailable. ';
    vscode.window.showInformationMessage('AI response received. '+measurement+'Not billed usage or whole-chat savings. View ATOF for the local request report.');
  } catch (_) { safeError('AI request failed or permission was denied. No automatic retry was attempted.'); }
}
async function optimizeSelection(){
  try {
    trustedLocal();
    const editor=vscode.window.activeTextEditor;
    if(!editor||editor.selection.isEmpty) return vscode.window.showInformationMessage('Select text first.');
    const content=editor.document.getText(editor.selection);
    const task=await vscode.window.showInputBox({prompt:'Task for local candidate only',value:'Explain the selected content'});
    if(!task) return;
    const ok=await vscode.window.showWarningMessage('Send selected text to local ATOF only?',{modal:true},'Optimize');
    if(ok!=='Optimize') return;
    const r=await api('/v1/optimize','POST',buildRequest(task,content,budget()));
    const doc=await vscode.workspace.openTextDocument({language:'plaintext',content:r.optimized_context||content});
    await vscode.window.showTextDocument(doc,{preview:true});
  } catch (_) { safeError('Local candidate unavailable. Original editor content was not changed.'); }
}
function activate(ctx) {
  const status=vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right,90);
  status.command='atof.openDashboard';status.text='$(shield) ATOF';status.show();
  ctx.subscriptions.push(status);
  if(vscode.lm?.registerTool && vscode.LanguageModelToolResult && vscode.LanguageModelTextPart){
    ctx.subscriptions.push(vscode.lm.registerTool(TOOL_NAME,{
      prepareInvocation(options){return {invocationMessage:'ATOF: read and optimize source',confirmationMessages:{title:'Allow ATOF source retrieval?',message:'Read authorized source in this trusted workspace, send it to local ATOF and return evidence to Copilot: '+String(options.input?.path||'')}};},
      async invoke(options,token){
        const result=await readContext({input:options.input,token,api,budget:budget(),trusted:()=>vscode.workspace.isTrusted&&!vscode.env.remoteName,roots:()=> (vscode.workspace.workspaceFolders||[]).filter(f=>f.uri.scheme==='file').map(f=>f.uri.fsPath)});
        return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(result)]);
      }
    }));
  }
  let refreshing=false;
  const refresh=async()=>{if(refreshing)return;refreshing=true;try{await controlStatus(status)}finally{refreshing=false}};
  const timer=setInterval(refresh,10000);ctx.subscriptions.push({dispose:()=>clearInterval(timer)});refresh();
  const event=new vscode.EventEmitter();ctx.subscriptions.push(event);
  const KEY='atof.approvedMcpPython';
  function approvedPython() {
    if(!vscode.workspace.isTrusted||vscode.env.remoteName) return undefined;
    const value=ctx.globalState.get(KEY);
    if(typeof value!=='string'||!path.isAbsolute(value)) return undefined;
    try {return fs.statSync(value).isFile()?value:undefined;}catch(_){return undefined;}
  }
  if(vscode.lm?.registerMcpServerDefinitionProvider&&vscode.McpStdioServerDefinition){
    ctx.subscriptions.push(vscode.lm.registerMcpServerDefinitionProvider('atof.localMcp',{
      onDidChangeMcpServerDefinitions:event.event,
      provideMcpServerDefinitions:()=>{
        const python=approvedPython();if(!python)return [];
        const server=new vscode.McpStdioServerDefinition('ATOF Copilot (explicit tool)',python,
          ['-I','-m','atof.mcp_server','--agent','copilot'],
          {'ATOF_ANALYTICS_ENABLED':'1','ATOF_MCP_SMOKE_TEST':null},'0.8.0');
        server.cwd=vscode.Uri.file(path.dirname(python));return [server];
      },
      resolveMcpServerDefinition:server=>approvedPython()===server.command?server:undefined
    }));
  }
  async function configureCopilot(){
    try{
      trustedLocal();
      if(!vscode.lm?.registerMcpServerDefinitionProvider||!vscode.McpStdioServerDefinition) return safeError('This VS Code version does not support extension MCP definitions.');
      const selected=await vscode.window.showOpenDialog({canSelectMany:false,canSelectFiles:true,canSelectFolders:false,openLabel:'Select approved ATOF virtual environment Python'});
      if(!selected?.length||selected[0].scheme!=='file') return;
      const python=selected[0].fsPath;
      if(!path.isAbsolute(python)||!/^python(?:3(?:\.\d+)?)?(?:\.exe)?$/i.test(path.basename(python))||!fs.statSync(python).isFile()) return safeError('Select the Python executable from the installed ATOF virtual environment.');
      const confirmed=await vscode.window.showWarningMessage('Register this local ATOF Python executable for optional Copilot MCP? Do not add it if an ATOF MCP server is already configured. VS Code and organization approvals still apply.\n'+python,{modal:true},'Register');
      if(confirmed!=='Register')return;
      await ctx.globalState.update(KEY,python);event.fire();
      vscode.window.showInformationMessage('ATOF MCP definition registered. Start/approve it in MCP: List Servers. Registration is not proof of a live connection.');
    }catch(_){safeError('MCP registration was not completed.');}
  }
  async function disableCopilot(){
    await ctx.globalState.update(KEY,undefined);event.fire();
    vscode.window.showInformationMessage('Extension-provided MCP definition removed. Stop an existing running MCP server through VS Code if needed.');
  }
  const commands={'atof.openDashboard':dashboard,'atof.toggleOptimization':()=>toggle(status),
    'atof.askAI':askAI,'atof.optimizeSelection':optimizeSelection,
    'atof.configureCopilot':configureCopilot,'atof.disableCopilot':disableCopilot};
  for(const [id,fn] of Object.entries(commands))ctx.subscriptions.push(vscode.commands.registerCommand(id,fn));
}
function deactivate(){}
module.exports={activate,deactivate};
