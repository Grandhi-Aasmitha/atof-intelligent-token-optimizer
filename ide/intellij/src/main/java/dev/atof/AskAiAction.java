package dev.atof;

import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.progress.Task;
import com.intellij.openapi.project.DumbAware;
import org.jetbrains.annotations.NotNull;

public final class AskAiAction extends AnAction implements DumbAware {
    @Override public @NotNull ActionUpdateThread getActionUpdateThread(){return ActionUpdateThread.BGT;}
    @Override public void update(@NotNull AnActionEvent e){e.getPresentation().setEnabled(e.getProject()!=null);}
    @Override public void actionPerformed(@NotNull AnActionEvent e){
        Project project=e.getProject();if(project==null||project.isDisposed())return;
        Editor editor=e.getData(CommonDataKeys.EDITOR);
        String selection=editor==null?null:editor.getSelectionModel().getSelectedText();
        String text=selection==null?"":selection;
        String task=Messages.showInputDialog(project,"Single-turn AI task","ATOF Ask AI",null);
        if(task==null||task.isBlank())return;
        try{Evidence.validate(task,text);}catch(IllegalArgumentException ex){Messages.showErrorDialog(project,ex.getMessage(),"ATOF");return;}
        int chosen=Messages.showChooseDialog(project,"Select an organization-approved provider API","ATOF",
            null,new String[]{"OpenAI API","Gemini API"},"OpenAI API");
        if(chosen<0)return;
        ProviderSender.Provider provider=ProviderSender.Provider.values()[chosen];
        String key=System.getenv(provider.key);
        if(key==null||key.isBlank()){Messages.showWarningDialog(project,"Approved "+provider.key+" is not available to the IDE process. No request was sent.","ATOF");return;}
        String model=Messages.showInputDialog(project,"Approved provider model ID","ATOF",null);
        if(model==null)return;
        try{ProviderSender.validateModel(model);}catch(IllegalArgumentException ex){Messages.showErrorDialog(project,"Invalid model ID.","ATOF");return;}
        if(Messages.showYesNoDialog(project,"Send the task and "+text.length()+" selected characters to local ATOF, then only the prepared input to "+provider.label+" / "+model+"? This may incur API charges. Use only authorized data.","ATOF consent",null)!=Messages.YES)return;
        ProgressManager.getInstance().run(new Task.Backgroundable(project,"ATOF: Preparing and Sending AI Request",true){
            @Override public void run(@NotNull ProgressIndicator indicator){
                try{
                    indicator.checkCanceled();
                    String prompt=new AtofClient().prepare(provider.adapter,task,text);
                    indicator.checkCanceled();
                    String answer=ProviderSender.send(provider,model,prompt,key);
                    indicator.checkCanceled();
                    ApplicationManager.getApplication().invokeLater(()->{
                        if(!project.isDisposed())AnswerView.show(project,answer,"ATOF AI response");
                    });
                }catch(com.intellij.openapi.progress.ProcessCanceledException ex){throw ex;}
                catch(Exception ex){
                    if(!indicator.isCanceled())ApplicationManager.getApplication().invokeLater(()->{
                        if(!project.isDisposed())Messages.showErrorDialog(project,"Preparation or provider request failed. No automatic retry or raw-context fallback was attempted.","ATOF");
                    });
                }
            }
        });
    }
}
