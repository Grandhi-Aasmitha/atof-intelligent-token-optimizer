package dev.atof;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import javax.swing.*;
import java.awt.*;

final class AnswerView extends DialogWrapper {
    private final String answer;
    private AnswerView(Project project,String answer,String title){
        super(project);this.answer=answer;setTitle(title);init();
    }
    @Override protected JComponent createCenterPanel(){
        JTextArea text=new JTextArea(answer,24,80);
        text.setEditable(false);text.setLineWrap(true);text.setWrapStyleWord(true);text.setCaretPosition(0);
        JScrollPane scroll=new JScrollPane(text);scroll.setPreferredSize(new Dimension(720,460));return scroll;
    }
    static void show(Project project,String answer,String title){new AnswerView(project,answer,title).show();}
}
