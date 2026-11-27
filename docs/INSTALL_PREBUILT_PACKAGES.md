# Install ATOF without local build tools

Build workflow: [ATOF installable packages](https://github.com/Grandhi-Aasmitha/atof-intelligent-token-optimizer/actions/workflows/package-atof.yml).
Select a successful job from a run for feature/phase-1-foundation and the desired commit. Each job independently uploads its package after build/shape checks. GitHub wraps each artifact in a download ZIP: extract that outer ZIP first, then use the inner file. Artifacts are retained for 30 days. No marketplace publication, release tag or unsigned installer execution is automated.

| Artifact | Inner file | Installation |
| --- | --- | --- |
| ATOF-IntelliJ | ATOF-IntelliJ.zip | IntelliJ Settings > Plugins > gear > Install Plugin from Disk; select the inner ZIP. Target 2025.2 (252.*). |
| ATOF-VSCode | ATOF-VSCode.vsix | Extensions > ... > Install from VSIX; select inner VSIX. VS Code 1.105+. |
| ATOF-Eclipse | ATOF-Eclipse.zip | Help > Install New Software > Add > Archive; select p2 ZIP. Approved dependencies may still be needed. |
| ATOF-Browser | ATOF-Browser.zip | Extract inner ZIP; load unpacked folder only if permitted by browser policy. |
| ATOF-Core-Windows | ATOF-Core-Windows.zip | Extract inner ZIP, run install_atof.cmd and run_atof.cmd with Python 3.11 x64 already installed. |

Verify the inner file SHA256 using Get-FileHash -Algorithm SHA256 and compare SHA256SUMS.txt. BUILD-INFO.json identifies the source commit. Checksums are integrity metadata, not signing or proof of runtime compatibility. Follow organization policy for unsigned packages. Do not disable security or install restrictions.

Use one shared local service on port 8081. You can keep using the existing source launcher instead of the Windows bundle:
~~~powershell
py -3.11 scripts/start_atof.py --port 8081
~~~
Open http://127.0.0.1:8081/dashboard. Stop any older process you own on that port before starting the new service. Your normal Java Maven projects are unaffected. The IntelliJ CI job uses Maven, JDK 21 and a pinned IntelliJ SDK; VSCE and Maven/Tycho run in separate CI jobs. The engine still needs Python. This is not a standalone EXE installer.

## Build status
A push affecting packaging or runtime sources on feature/phase-1-foundation requests an automatic run if Actions are enabled and permitted. Manual workflow dispatch is available once the workflow exists on the default branch. No new branch or PR is needed for the push trigger. Do not assume the files exist until the specific job succeeds and the Artifacts section contains them. If a job fails, inspect its logs; other successful jobs can still produce artifacts. Existing regression CI stays separate. Package builds do not establish live AI compatibility, production acceptance or completion of Phase 10's remaining features.

Build jobs use the repository's existing SDK targets, read-only repository permissions, standard GitHub-hosted runners and versioned build tools. No AI API credentials, public package publishing or organization security settings are required or changed. If hosted builds or external dependency downloads are disallowed, use approved internal build infrastructure instead.
