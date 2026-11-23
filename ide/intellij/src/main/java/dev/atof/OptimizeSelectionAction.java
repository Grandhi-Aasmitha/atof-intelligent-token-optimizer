package dev.atof;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.application.ApplicationManager;
import org.jetbrains.annotations.NotNull;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

public class OptimizeSelectionAction extends AnAction {
  @Override public @NotNull ActionUpdateThread getActionUpdateThread(){return ActionUpdateThread.BGT;}
  @Override public void update(@NotNull AnActionEvent e){
    Editor editor=e.getData(CommonDataKeys.EDITOR);
    e.getPresentation().setEnabledAndVisible(editor!=null&&editor.getSelectionModel().hasSelection());
  }
  @Override public void actionPerformed(@NotNull AnActionEvent e){
    Editor editor=e.getData(CommonDataKeys.EDITOR);
    Project project=e.getProject();
    if(editor==null||project==null)return;
    String text=editor.getSelectionModel().getSelectedText();
    if(text==null||text.isBlank())return;
    if(text.length()>300000){Messages.showWarningDialog(project,"Selection too large","ATOF");return;}
    String[] kinds={"source","error","test","diff"};
    int kind=Messages.showChooseDialog(project,"Evidence type","ATOF Local Optimization",
      new String[]{"Source","Error","Test","Diff"},"Source",null);
    if(kind<0)return;
    String task=Messages.showInputDialog(project,"Optimization task","ATOF",null,
      "Explain relevant evidence",null);
    if(task==null||task.isBlank())return;
    if(Messages.showYesNoDialog(project,"Send selected text to local ATOF?","ATOF consent",null)!=Messages.YES)return;
    String json="{\"ide\":\"intellij\",\"task\":"+quote(task)+",\"text\":"+quote(text)+
      ",\"evidence_kind\":"+quote(kinds[kind])+"}";
    ApplicationManager.getApplication().executeOnPooledThread(()->{
      try{
        HttpRequest req=HttpRequest.newBuilder(URI.create("http://127.0.0.1:8080/v1/ide/optimize"))
          .timeout(Duration.ofSeconds(15)).header("Content-Type","application/json")
          .POST(HttpRequest.BodyPublishers.ofString(json,StandardCharsets.UTF_8)).build();
        HttpResponse<String> result=HttpClient.newHttpClient().send(req,HttpResponse.BodyHandlers.ofString());
        if(result.statusCode()!=200)throw new IllegalStateException("HTTP "+result.statusCode());
        String body=result.body();
        ApplicationManager.getApplication().invokeLater(()->Messages.showInfoMessage(project,
            body.length()>6500?body.substring(0,6500)+"\n[Preview truncated]":body,
            "ATOF candidate — model consumption unverified"));
      }catch(Exception ex){
        ApplicationManager.getApplication().invokeLater(()->Messages.showErrorDialog(project,
            "ATOF local connection failed: "+ex.getClass().getSimpleName(),"ATOF"));
      }
    });
  }
  private static String quote(String value){
    StringBuilder s=new StringBuilder("\"");
    for(int i=0;i<value.length();i++){
      char c=value.charAt(i);
      switch(c){
        case '"'->s.append("\\\"");
        case '\\'->s.append("\\\\");
        case '\n'->s.append("\\n");
        case '\r'->s.append("\\r");
        case '\t'->s.append("\\t");
        default->{if(c<32)s.append(String.format("\\u%04x",(int)c));else s.append(c);}
      }
    }
    return s.append('"').toString();
  }
}
