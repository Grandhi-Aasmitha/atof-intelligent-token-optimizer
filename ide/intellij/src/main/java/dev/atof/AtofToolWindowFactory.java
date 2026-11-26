package dev.atof;

import com.intellij.ide.BrowserUtil;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowFactory;
import com.intellij.ui.content.Content;
import com.intellij.ui.content.ContentFactory;
import com.google.gson.JsonObject;
import org.jetbrains.annotations.NotNull;
import javax.swing.*;
import java.awt.*;

/** Control shortcuts only. Reporting remains in the single web dashboard. */
public final class AtofToolWindowFactory implements ToolWindowFactory {
    @Override public void createToolWindowContent(@NotNull Project project,@NotNull ToolWindow toolWindow){
        JPanel panel=new JPanel(new GridLayout(0,1,6,6));
        JLabel state=new JLabel("ATOF: checking local service");
        JLabel note=new JLabel("AI connection: unverified");
        JButton refresh=new JButton("Refresh"),on=new JButton("ON"),off=new JButton("OFF"),dashboard=new JButton("Open Control Center");
        panel.add(state);panel.add(note);panel.add(on);panel.add(off);panel.add(refresh);panel.add(dashboard);
        class Control {
            boolean busy=false, disposed=false;
            void load(Boolean enabled){
                if(busy||disposed||project.isDisposed())return;
                busy=true;on.setEnabled(false);off.setEnabled(false);refresh.setEnabled(false);
                ApplicationManager.getApplication().executeOnPooledThread(()->{
                    JsonObject result=null;
                    try{AtofClient client=new AtofClient();result=enabled==null?client.control():client.enabled(enabled);}
                    catch(Exception ignored){}
                    JsonObject data=result;
                    ApplicationManager.getApplication().invokeLater(()->{
                        if(disposed||project.isDisposed())return;
                        busy=false;refresh.setEnabled(true);
                        if(data==null||!data.get("available").getAsBoolean()){
                            state.setText("ATOF unavailable — start local service");return;
                        }
                        boolean active=data.getAsJsonObject("settings").get("enabled").getAsBoolean();
                        state.setText("ATOF: "+(active?"ON":"OFF"));on.setEnabled(!active);off.setEnabled(active);
                    });
                });
            }
        }
        Control control=new Control();
        on.addActionListener(e->control.load(true));off.addActionListener(e->control.load(false));
        refresh.addActionListener(e->control.load(null));
        dashboard.addActionListener(e->{try{BrowserUtil.browse(new AtofClient().dashboard().toString());}
            catch(Exception ignored){state.setText("Invalid local ATOF URL");}});
        Timer timer=new Timer(10000,e->{if(panel.isShowing())control.load(null);});timer.start();
        Content content=ContentFactory.getInstance().createContent(panel,"",false);
        content.setDisposer(()->{control.disposed=true;timer.stop();});
        toolWindow.getContentManager().addContent(content);control.load(null);
    }
}
