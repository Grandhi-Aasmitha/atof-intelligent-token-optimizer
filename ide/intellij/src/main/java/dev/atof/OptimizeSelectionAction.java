package dev.atof;

import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.application.ApplicationManager;
import com.google.gson.JsonObject;
import org.jetbrains.annotations.NotNull;

public final class OptimizeSelectionAction extends AnAction {
    @Override public @NotNull ActionUpdateThread getActionUpdateThread(){return ActionUpdateThread.BGT;}
    @Override public void update(@NotNull AnActionEvent e){
        Editor editor=e.getData(CommonDataKeys.EDITOR);
        e.getPresentation().setEnabledAndVisible(editor!=null&&editor.getSelectionModel().hasSelection());
    }
    @Override public void actionPerformed(@NotNull AnActionEvent e){
        Editor editor=e.getData(CommonDataKeys.EDITOR);Project project=e.getProject();
        if(editor==null||project==null)return;
        String text=editor.getSelectionModel().getSelectedText();if(text==null||text.isBlank())return;
        String task=Messages.showInputDialog(project,"Task for local candidate only","ATOF",null);
        if(task==null)return;
        try{Evidence.validate(task,text);}catch(IllegalArgumentException ex){Messages.showErrorDialog(project,ex.getMessage(),"ATOF");return;}
        if(Messages.showYesNoDialog(project,"Send selected text to local ATOF only?","ATOF consent",null)!=Messages.YES)return;
        ApplicationManager.getApplication().executeOnPooledThread(()->{
            try{
                JsonObject r=new AtofClient().candidate(task,text);
                String value=r.has("optimized_context")&&!r.get("optimized_context").isJsonNull()?r.get("optimized_context").getAsString():text;
                ApplicationManager.getApplication().invokeLater(()->{if(!project.isDisposed())AnswerView.show(project,value,"ATOF local candidate — not sent to AI");});
            }catch(Exception ex){ApplicationManager.getApplication().invokeLater(()->{if(!project.isDisposed())Messages.showErrorDialog(project,"Local ATOF unavailable. Editor content was not changed.","ATOF");});}
        });
    }
}
