# Phase 7 — Supported IDE workflows

The standalone local API allows selected editor text to be submitted with explicit consent via POST /v1/ide/optimize. Caller sends {ide, task, evidence_kind, text, optional path_label and token_budget}; no automatic workspace reading or source modification occurs.

## VS Code

Open ide/vscode in VS Code as an extension development workspace, press F5. Start FastAPI on loopback only and select a synthetic error log in the editor. Command Palette → ATOF: Optimize Selection. After approving, an untitled document shows estimates and an optimization candidate. The source editor must remain unchanged.

## IntelliJ IDEA

Open ide/intellij using JDK 21 and Gradle 9+; build with IntelliJ Platform Gradle Plugin 2.20.1. Run Gradle runIde. Select synthetic code/log, right-click ATOF: Optimize Selection, approve and inspect the read-only result dialog. IntelliJ plugin compilation and IDE smoke testing require an actual IntelliJ environment and are not yet verified here.

## Security

The server is unauthenticated in development and must bind only to 127.0.0.1. Do not send confidential code/logs unless authorized. Explicit selection is not equivalent to transparent optimization of a built-in AI assistant's model requests.

## Acceptance

python -m pytest tests/test_phase7.py -q. Independently validate VS Code Extension Development Host and IntelliJ Gradle plugin builds.
