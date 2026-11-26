package dev.atof;

import com.intellij.ide.BrowserUtil;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.ui.Messages;
import org.jetbrains.annotations.NotNull;

public final class OpenDashboardAction extends AnAction {
    @Override public void actionPerformed(@NotNull AnActionEvent event){
        try { BrowserUtil.browse(new AtofClient().dashboard().toString()); }
        catch(Exception ex){Messages.showErrorDialog(event.getProject(),"Check the local ATOF service URL.","ATOF");}
    }
}
