package dev.atof.eclipse;

import com.google.gson.JsonObject;
import org.eclipse.core.runtime.IProgressMonitor;
import org.eclipse.core.runtime.IStatus;
import org.eclipse.core.runtime.Status;
import org.eclipse.core.runtime.jobs.Job;
import org.eclipse.jface.dialogs.InputDialog;
import org.eclipse.jface.dialogs.MessageDialog;
import org.eclipse.jface.text.ITextSelection;
import org.eclipse.jface.viewers.ISelection;
import org.eclipse.jface.viewers.ISelectionProvider;
import org.eclipse.jface.window.Window;
import org.eclipse.swt.SWT;
import org.eclipse.swt.layout.GridData;
import org.eclipse.swt.layout.GridLayout;
import org.eclipse.swt.widgets.*;
import org.eclipse.ui.IEditorPart;
import org.eclipse.ui.part.ViewPart;
import org.eclipse.ui.PlatformUI;

/** Local controls only; no second reporting dashboard and no native agent interception. */
public final class ControlView extends ViewPart {
    public static final String ID="dev.atof.eclipse.control";
    private Composite panel;
    private Display display;
    private Label status;
    private Button on,off,refresh;
    private boolean busy;
    private volatile boolean disposed;
    private Job controlJob,askJob;
    private final Runnable poll=new Runnable(){
        @Override public void run(){
            if(disposed||panel==null||panel.isDisposed())return;
            if(panel.isVisible())updateControl(null);
            display.timerExec(10000,this);
        }
    };
    @Override public void createPartControl(Composite parent){
        display=parent.getDisplay();
        panel=new Composite(parent,SWT.NONE);panel.setLayout(new GridLayout(1,false));
        status=new Label(panel,SWT.WRAP);status.setLayoutData(new GridData(SWT.FILL,SWT.TOP,true,false));
        status.setText("Checking local ATOF…");
        Label note=new Label(panel,SWT.WRAP);note.setLayoutData(new GridData(SWT.FILL,SWT.TOP,true,false));
        note.setText("Native AI connection: unverified");
        on=button("Optimization ON",()->updateControl(true));
        off=button("Optimization OFF",()->updateControl(false));
        refresh=button("Refresh",()->updateControl(null));
        button("Open Control Center",this::dashboard);
        Label optional=new Label(panel,SWT.WRAP);optional.setLayoutData(new GridData(SWT.FILL,SWT.TOP,true,false));
        optional.setText("Optional: single-turn approved API request, using selected editor text only.");
        button("Ask AI — OpenAI API",()->ask(ProviderSender.Provider.OPENAI));
        button("Ask AI — Gemini API",()->ask(ProviderSender.Provider.GEMINI));
        updateControl(null);display.timerExec(10000,poll);
    }
    private Button button(String text,Runnable action){
        Button b=new Button(panel,SWT.PUSH);b.setText(text);b.setLayoutData(new GridData(SWT.FILL,SWT.CENTER,true,false));
        b.addListener(SWT.Selection,e->action.run());return b;
    }
    private void ui(Runnable action){
        if(disposed||display==null||display.isDisposed())return;
        display.asyncExec(()->{if(!disposed&&panel!=null&&!panel.isDisposed())action.run();});
    }
    private void updateControl(Boolean enabled){
        if(busy||disposed)return;busy=true;on.setEnabled(false);off.setEnabled(false);refresh.setEnabled(false);
        controlJob=new Job("ATOF local controls"){
            @Override protected IStatus run(IProgressMonitor monitor){
                JsonObject result=null;
                try{
                    if(!monitor.isCanceled()){
                        AtofClient client=new AtofClient();
                        result=enabled==null?client.control():client.enabled(enabled);
                    }
                }catch(Exception ignored){}
                JsonObject data=result;
                ui(()->{
                    busy=false;refresh.setEnabled(true);
                    try{
                        if(data==null||!data.get("available").getAsBoolean())throw new IllegalStateException();
                        boolean active=data.getAsJsonObject("settings").get("enabled").getAsBoolean();
                        status.setText("ATOF: "+(active?"ON":"OFF"));
                        on.setEnabled(!active);off.setEnabled(active);
                    }catch(Exception ignored){status.setText("ATOF unavailable — start the shared local service");}
                    panel.layout();
                });
                return monitor.isCanceled()?Status.CANCEL_STATUS:Status.OK_STATUS;
            }
        };
        controlJob.setSystem(true);controlJob.schedule();
    }
    private void dashboard(){
        try{PlatformUI.getWorkbench().getBrowserSupport().getExternalBrowser().openURL(new AtofClient().dashboard().toURL());}
        catch(Exception ex){MessageDialog.openError(panel.getShell(),"ATOF","Cannot open local Control Center. Check service URL.");}
    }
    private String selectedText(){
        IEditorPart editor=getSite().getPage().getActiveEditor();
        if(editor==null)return "";
        ISelectionProvider provider=editor.getSite().getSelectionProvider();
        if(provider==null)return "";
        ISelection selected=provider.getSelection();
        return selected instanceof ITextSelection text?text.getText():"";
    }
    private void ask(ProviderSender.Provider provider){
        if(disposed||askJob!=null&&askJob.getState()!=Job.NONE)return;
        String text=selectedText();
        if(text==null)text="";
        final String evidence=text;
        String key=System.getenv(provider.key);
        if(key==null||key.isBlank()){
            MessageDialog.openWarning(panel.getShell(),"ATOF","Approved "+provider.key+" is not available to the Eclipse process. No request sent.");return;
        }
        InputDialog taskInput=new InputDialog(panel.getShell(),"ATOF Ask AI","Single-turn task (optional selected editor context)","",s->s.isBlank()?"Task required":null);
        if(taskInput.open()!=Window.OK)return;
        String task=taskInput.getValue();
        try{Evidence.validate(task,evidence);}catch(IllegalArgumentException ex){MessageDialog.openError(panel.getShell(),"ATOF",ex.getMessage());return;}
        InputDialog modelInput=new InputDialog(panel.getShell(),"ATOF","Organization-approved model ID","",s->{
            try{ProviderSender.validateModel(s);return null;}catch(IllegalArgumentException ex){return "Invalid model ID";}
        });
        if(modelInput.open()!=Window.OK)return;
        String model=modelInput.getValue();
        if(!MessageDialog.openQuestion(panel.getShell(),"ATOF consent","Send task and "+evidence.length()+" selected characters to local ATOF, then only the prepared input to "+provider.label+" / "+model+"? This may incur API charges. Use authorized data only."))return;
        askJob=new Job("ATOF: Prepare and send AI request"){
            @Override protected IStatus run(IProgressMonitor monitor){
                try{
                    if(monitor.isCanceled()||disposed)return Status.CANCEL_STATUS;
                    String prompt=new AtofClient().prepare(provider.adapter,task,evidence);
                    if(monitor.isCanceled()||disposed)return Status.CANCEL_STATUS;
                    String answer=ProviderSender.send(provider,model,prompt,key);
                    if(monitor.isCanceled()||disposed)return Status.CANCEL_STATUS;
                    ui(()->showAnswer(answer));
                }catch(Exception ex){
                    if(!monitor.isCanceled())ui(()->MessageDialog.openError(panel.getShell(),"ATOF","Preparation or provider request failed. No automatic retry or original-context fallback was attempted."));
                }
                return monitor.isCanceled()?Status.CANCEL_STATUS:Status.OK_STATUS;
            }
        };
        askJob.setUser(true);askJob.schedule();
    }
    private void showAnswer(String answer){
        Shell shell=new Shell(panel.getShell(),SWT.DIALOG_TRIM|SWT.RESIZE);
        shell.setText("ATOF AI response — provider savings unverified");shell.setLayout(new GridLayout(1,false));
        Text output=new Text(shell,SWT.MULTI|SWT.READ_ONLY|SWT.WRAP|SWT.V_SCROLL|SWT.BORDER);
        output.setLayoutData(new GridData(SWT.FILL,SWT.FILL,true,true));output.setText(answer);
        Button close=new Button(shell,SWT.PUSH);close.setText("Close");close.addListener(SWT.Selection,e->shell.dispose());
        shell.setSize(760,500);shell.open();
    }
    @Override public void setFocus(){if(refresh!=null&&!refresh.isDisposed())refresh.setFocus();}
    @Override public void dispose(){
        disposed=true;
        if(display!=null&&!display.isDisposed())display.timerExec(-1,poll);
        if(controlJob!=null)controlJob.cancel();
        if(askJob!=null)askJob.cancel();
        super.dispose();
    }
}
