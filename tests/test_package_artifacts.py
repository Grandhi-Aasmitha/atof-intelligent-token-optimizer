import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("package_artifacts",ROOT/"scripts/package_artifacts.py")
pack=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


def archive(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path,"w") as z:
        for name,data in entries.items():
            z.writestr(name,data)


def test_browser_build_and_digest(tmp_path,monkeypatch):
    import shutil
    shutil.copytree(ROOT/"ide/browser",tmp_path/"ide/browser")
    monkeypatch.setenv("GITHUB_SHA","test-commit")
    path=pack.stage("browser",tmp_path)
    assert path.name=="ATOF-Browser.zip"
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist())=={"manifest.json","popup.html","README.md"}
    info=json.loads((path.parent/"BUILD-INFO.json").read_text())
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert info["sha256"]==digest and info["commit"]=="test-commit"
    assert info["runtime_integration_verified"] is False
    assert (path.parent/"SHA256SUMS.txt").read_text().strip()==f"{digest}  {path.name}"
    with pytest.raises(ValueError,match="staging must be empty"):
        pack.stage("browser",tmp_path)


def test_browser_rejects_permission_escalation(tmp_path):
    source=tmp_path/"ide/browser"
    source.mkdir(parents=True)
    (source/"manifest.json").write_text(json.dumps({"manifest_version":3,"host_permissions":["<all_urls>"]}))
    with pytest.raises(ValueError,match="Unexpected browser permissions"):
        pack.stage("browser",tmp_path)


def test_intellij_rejects_source_zip_and_accepts_expected_archive_shape(tmp_path):
    path=tmp_path/"ide/intellij/target/atof-intellij-0.9.1-plugin.zip"
    archive(path,{"src/main/java/Control.java":"source only"})
    with pytest.raises(ValueError,match="plugin JAR not found"):
        pack.stage("intellij",tmp_path)
    jar=io.BytesIO()
    with zipfile.ZipFile(jar,"w") as z:
        z.writestr("META-INF/plugin.xml","<idea-plugin><id>dev.atof.intellij.selection</id></idea-plugin>")
        # This tests archive structure only, not Java compilation.
        z.writestr("dev/atof/AtofToolWindowFactory.class",b"fixture")
    archive(path,{"atof/lib/plugin.jar":jar.getvalue()})
    assert pack.stage("intellij",tmp_path).read_bytes()==path.read_bytes()


def test_reject_unsafe_paths(tmp_path):
    path=tmp_path/"unsafe.zip"
    archive(path,{"../escape":"bad"})
    with zipfile.ZipFile(path) as z:
        with pytest.raises(ValueError,match="Unsafe archive path"):
            pack.inspect_archive(z)


def test_vscode_archive_structure(tmp_path):
    path=tmp_path/"ide/vscode/ATOF-VSCode.vsix"
    archive(path,{"extension/package.json":"{}"})
    with pytest.raises(ValueError,match="runtime files missing"):
        pack.stage("vscode",tmp_path)
    archive(path,{"extension/package.json":json.dumps({"name":"atof-selection-optimizer","publisher":"atof-local"}),
                  "extension.vsixmanifest":"fixture","[Content_Types].xml":"fixture",
                  "extension/extension.js":"fixture","extension/client.js":"fixture","extension/owned.js":"fixture"})
    assert pack.stage("vscode",tmp_path).read_bytes()==path.read_bytes()
