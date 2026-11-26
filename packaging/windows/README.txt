ATOF Windows engine bundle (Python 3.11 x64 required)

1. Extract the entire inner ATOF-Core-Windows.zip into a writable folder.
2. Open a terminal in the extracted folder and run install_atof.cmd.
3. Run run_atof.cmd, then open http://127.0.0.1:8081/dashboard.

Wheels are installed in a private .venv without fetching dependencies.
No administrator privileges, Gradle, Maven, Node or policy changes required.
Approved Python 3.11 x64 must already be available via the py launcher.
Use the existing source launcher instead if preferred; do not run both on 8081.
The control and analytics stores remain under the current user's .atof folder
unless environment variables override them. No provider credentials included.
Native agent interception and actual provider token savings remain unverified.
This is a portable Python bundle, not a standalone signed Windows EXE.
