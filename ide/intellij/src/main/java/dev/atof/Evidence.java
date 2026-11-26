package dev.atof;

import java.util.regex.Pattern;

/** Classification of user-selected text, not filesystem or repository discovery. */
public final class Evidence {
    private Evidence() {}
    private static final Pattern DIFF = Pattern.compile("^diff --git ", Pattern.MULTILINE);
    private static final Pattern HUNK = Pattern.compile("^@@ ", Pattern.MULTILINE);
    private static final Pattern TEST = Pattern.compile("(?m)^\\s*(?:test_[^\\n]+|Tests run:)");
    private static final Pattern STATUS = Pattern.compile("\\b(?:PASSED|FAILED)\\b");
    private static final Pattern ERROR = Pattern.compile("Traceback \\(most recent call last\\)|(?m)^\\s*[\\w.]+(?:Error|Exception):");

    public static String slot(String text) {
        if (DIFF.matcher(text).find() && HUNK.matcher(text).find()) return "diff";
        if (TEST.matcher(text).find() && STATUS.matcher(text).find()) return "test_output";
        if (ERROR.matcher(text).find()) return "error_output";
        return "context";
    }

    public static void validate(String task, String text) {
        if (task == null || task.isBlank() || task.codePointCount(0,task.length()) > 20000)
            throw new IllegalArgumentException("Task must contain 1–20,000 characters");
        if (text == null || text.codePointCount(0,text.length()) > 300000)
            throw new IllegalArgumentException("Selection exceeds 300,000 characters");
    }
}
