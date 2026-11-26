"""Stage actual build outputs, validate archive shape and write SHA-256 metadata.

No compilation, downloads, provider calls or credentials. Fail instead of
substituting source ZIPs for compiled plugins. Run from any directory.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def only(paths):
    paths = sorted(paths)
    require(len(paths) == 1, f"Expected exactly one build output, got {len(paths)}")
    return paths[0]


def inspect_archive(archive):
    names = archive.namelist()
    require(bool(names) and len(set(names)) == len(names), "Empty or duplicate archive entries")
    for name in names:
        p = PurePosixPath(name)
        require(not p.is_absolute() and ".." not in p.parts and "\\" not in name
                and ":" not in name, "Unsafe archive path")
    require(archive.testzip() is None, "Archive integrity check failed")
    return set(names)


def verify_intellij(path):
    with zipfile.ZipFile(path) as outer:
        names = inspect_archive(outer)
        matches = 0
        for name in sorted(n for n in names if n.endswith(".jar") and "/lib/" in n):
            with zipfile.ZipFile(io.BytesIO(outer.read(name))) as jar:
                if "META-INF/plugin.xml" not in jar.namelist():
                    continue
                root = ET.fromstring(jar.read("META-INF/plugin.xml"))
                if root.findtext("id") == "dev.atof.intellij.selection":
                    require("dev/atof/AtofToolWindowFactory.class" in jar.namelist(), "Compiled IntelliJ view missing")
                    matches += 1
        require(matches == 1, "ATOF IntelliJ plugin JAR not found")


def verify_vscode(path):
    with zipfile.ZipFile(path) as z:
        names = inspect_archive(z)
        required = {"extension.vsixmanifest", "[Content_Types].xml",
                    "extension/package.json", "extension/extension.js",
                    "extension/client.js", "extension/owned.js"}
        require(required.issubset(names), "VSIX runtime files missing")
        pkg = json.loads(z.read("extension/package.json"))
        require(pkg["name"] == "atof-selection-optimizer" and pkg["publisher"] == "atof-local",
                "Wrong VSIX extension identity")


def zip_files(target, files):
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for source, name in sorted(files, key=lambda x: x[1]):
            require(source.is_file() and not source.is_symlink(), f"Missing or nonregular input: {source.name}")
            z.write(source, name)
    with zipfile.ZipFile(target) as z:
        inspect_archive(z)


def stage(kind, root=ROOT):
    output = root / "package-out" / kind
    output.mkdir(parents=True, exist_ok=True)
    require(not any(output.iterdir()), "Artifact staging must be empty")
    if kind == "intellij":
        source = only((root / "ide/intellij/build/distributions").glob("*.zip"))
        verify_intellij(source)
        target = output / "ATOF-IntelliJ.zip"
        shutil.copyfile(source, target)
    elif kind == "vscode":
        source = root / "ide/vscode/ATOF-VSCode.vsix"
        verify_vscode(source)
        target = output / "ATOF-VSCode.vsix"
        shutil.copyfile(source, target)
    elif kind == "eclipse":
        source = root / "ide/eclipse/dev.atof.eclipse.repository/target/repository"
        require(any((source / n).is_file() for n in ("content.jar", "content.xml", "content.xml.xz")), "Missing p2 content metadata")
        require(any((source / n).is_file() for n in ("artifacts.jar", "artifacts.xml", "artifacts.xml.xz")), "Missing p2 artifact metadata")
        plugin = only((source / "plugins").glob("dev.atof.eclipse_*.jar"))
        with zipfile.ZipFile(plugin) as jar:
            names = inspect_archive(jar)
            require({"META-INF/MANIFEST.MF", "plugin.xml", "dev/atof/eclipse/ControlView.class"}.issubset(names), "Compiled Eclipse plugin missing")
        require(any((source / "features").glob("dev.atof.eclipse.feature_*.jar")), "Eclipse feature missing")
        target = output / "ATOF-Eclipse.zip"
        zip_files(target, [(p, p.relative_to(source).as_posix()) for p in source.rglob("*") if p.is_file()])
    elif kind == "browser":
        source = root / "ide/browser"
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        require(manifest.get("manifest_version") == 3, "Expected Manifest V3")
        require(not any(manifest.get(k) for k in ("permissions","optional_permissions","host_permissions",
                    "optional_host_permissions","content_scripts","background","externally_connectable",
                    "web_accessible_resources")), "Unexpected browser permissions")
        require(manifest.get("action",{}).get("default_popup")=="popup.html", "Unexpected popup")
        target = output / "ATOF-Browser.zip"
        zip_files(target, [(source / n, n) for n in ("manifest.json","popup.html","README.md")])
    elif kind == "core":
        source = root / "package-staging/wheelhouse"
        wheels = sorted(source.glob("*.whl"))
        own = only(p for p in wheels if p.name.startswith("atof_intelligent_token_optimizer-"))
        with zipfile.ZipFile(own) as z:
            names = inspect_archive(z)
            require({"atof/api.py","atof/ui/dashboard.html","atof/ui/browser.js","atof/catalog/features.json"}.issubset(names), "Engine wheel missing runtime files")
        require(len(wheels)>1, "Dependency wheels missing")
        target = output / "ATOF-Core-Windows.zip"
        zip_files(target, [(p, "wheelhouse/"+p.name) for p in wheels]+
                  [(root/"packaging/windows"/n,n) for n in ("install_atof.cmd","run_atof.cmd","README.txt")])
    else:
        raise ValueError("Unknown package")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output/"SHA256SUMS.txt").write_text(f"{digest}  {target.name}\n",encoding="utf-8")
    (output/"BUILD-INFO.json").write_text(json.dumps({
        "package":target.name, "commit":os.getenv("GITHUB_SHA","local-unverified"),
        "workflow_run":os.getenv("GITHUB_RUN_ID"), "sha256":digest,
        "runtime_integration_verified":False,
    },indent=2)+"\n",encoding="utf-8")
    print(f"Staged {target.name}: {digest}")
    return target


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind",choices=["intellij","vscode","eclipse","browser","core"])
    stage(parser.parse_args().kind)
