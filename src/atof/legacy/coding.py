"""BLM-7: explicit, deterministic, opt-in coding context optimizers.

No filesystem access, Git subprocess, external retrieval, LLM calls, persistence,
network calls, or secret logging. The client supplies the authorized evidence.
Token counts are coarse estimates; omission is NEVER a proof of correctness.
"""
from __future__ import annotations

import ast
import hashlib
import re
import time
from typing import Any
from .intent_routing import legacy_developer_intent, route_intent
from .tokens import estimate_text

_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_STOP = {"the", "and", "this", "from", "with", "into", "that", "should", "when", "without", "please", "code", "file", "function", "fix", "make", "test", "need", "for", "app", "using"}
_ERRORS = re.compile(r"\b(error|exception|failed|failure|fatal|assert|traceback|caused by|cannot|timeout|unhandled|critical|panic)\b", re.I)
# No trailing \b: exception markers end in ":" so a trailing word boundary
# would make "KeyError: 'x'" non-critical and eligible for folding.
_TRACE = re.compile(r"\bFile \".+\", line \d+|\bat [\w.$<>]+\(.+:\d+\)|\b\w+(?:Error|Exception):|\bCaused by:", re.I)


def terms(text: str) -> set[str]:
    return {t.lower() for t in _IDENT.findall(text) if len(t) >= 3 and t.lower() not in _STOP}


def _budget(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 64 <= value <= 200_000:
        raise ValueError("token_budget must be an integer from 64 to 200000")
    return value


def validate_files(files: list[dict]) -> list[dict]:
    if not isinstance(files, list) or len(files) > 100:
        raise ValueError("files must be an array of at most 100 caller-supplied files")
    seen = set()
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"].strip():
            raise ValueError("every file requires a nonempty path")
        if not isinstance(item.get("content"), str) or len(item["content"]) > 300_000:
            raise ValueError("every file requires text content (max 300000 chars)")
        if item["path"] in seen:
            raise ValueError("duplicate file paths must be resolved by the caller")
        seen.add(item["path"])
    return files


def developer_intent(task: str) -> str:
    if not isinstance(task, str) or not task.strip() or len(task) > 20000:
        raise ValueError("task must be nonempty text of <=20000 chars")
    return legacy_developer_intent(route_intent(task))


def _score(task_terms: set[str], name: str, text: str, path: str) -> float:
    if not task_terms:
        return 0
    named = terms(name)
    body = terms(text[:10000]); path_terms = terms(path)
    return 5 * len(task_terms & named) + 3 * len(task_terms & path_terms) + len(task_terms & body)


def _module_name(path: str) -> str | None:
    normalized = path.replace('\\', '/')
    if not normalized.endswith('.py'):
        return None
    parts = normalized[:-3].split('/')
    if parts[-1] == '__init__':
        parts.pop()
    if not parts or not all(part.isidentifier() for part in parts):
        return None
    return '.'.join(parts)


def _module_aliases(path: str) -> set[str]:
    module = _module_name(path)
    if module is None:
        return set()
    parts = module.split('.')
    return {'.'.join(parts[index:]) for index in range(len(parts))}


def _relative_import_module(module: str | None, level: int, current: str | None,
                            package_init: bool = False) -> str | None:
    if level == 0:
        return module
    if current is None:
        return None
    parts = current.split('.')
    package = parts if package_init else parts[:-1]
    if level > len(package):
        return None
    keep = len(package) - level + 1
    base = package[:keep]
    if module:
        base.extend(module.split('.'))
    return '.'.join(base) or None


def _dotted_name(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return parent + [node.attr] if parent else None
    return None


def _candidates(path: str, content: str, query: set[str]) -> list[dict]:
    lines = content.splitlines()
    results: list[dict] = []
    if path.endswith('.py'):
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            tree = None
        if tree is not None:
            imports = [node for node in tree.body if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            import_text = '\n'.join(line for n in imports for line in lines[n.lineno-1:n.end_lineno])
            current_module = _module_name(path)
            imported_symbols: dict[str, tuple[str, str]] = {}
            imported_modules: dict[str, str] = {}
            for statement in imports:
                if isinstance(statement, ast.ImportFrom):
                    imported_module = _relative_import_module(
                        statement.module, statement.level, current_module,
                        path.replace('\\', '/').rsplit('/', 1)[-1] == '__init__.py')
                    if imported_module:
                        for alias in statement.names:
                            if alias.name != '*':
                                imported_symbols[alias.asname or alias.name] = (imported_module, alias.name)
                elif isinstance(statement, ast.Import):
                    for alias in statement.names:
                        local_name = alias.asname or alias.name.split('.')[0]
                        imported_modules[local_name] = alias.name if alias.asname else local_name
            # Top-level definitions are kept whole so decorators, signature,
            # and related implementation are never silently chopped in half.
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])]); end = node.end_lineno
                    text = '\n'.join(lines[start-1:end])
                    score = _score(query, node.name, text, path)
                    if isinstance(node, ast.ClassDef):
                        members = ' '.join(getattr(x, 'name', '') for x in node.body)
                        score += 5 * len(query & terms(members))
                    called = {child.func.id for child in ast.walk(node)
                              if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)}
                    dependency_refs = set()
                    for child in ast.walk(node):
                        if not isinstance(child, ast.Call):
                            continue
                        dotted = _dotted_name(child.func)
                        if not dotted:
                            continue
                        if len(dotted) == 1 and dotted[0] in imported_symbols:
                            dependency_refs.add(imported_symbols[dotted[0]])
                        elif dotted[0] in imported_modules and len(dotted) > 1:
                            dependency_refs.add((
                                '.'.join([imported_modules[dotted[0]], *dotted[1:-1]]),
                                dotted[-1],
                            ))
                    results.append({"path": path, "kind": type(node).__name__, "symbol": node.name,
                                    "start_line": start, "end_line": end, "text": text,
                                    "imports": import_text, "score": score, "dependencies": sorted(called),
                                    "module": current_module,
                                    "dependency_refs": sorted(dependency_refs)})
            if results:
                # A matching filename does not make every definition in that file relevant.
                symbol_scores = [_score(query, c['symbol'], c['text'], '') for c in results]
                if any(symbol_scores):
                    for candidate, score in zip(results, symbol_scores):
                        candidate['score'] = score
                return results
    # Other languages or invalid Python: preserve complete nearby line windows.
    matched = [i for i, line in enumerate(lines) if query & terms(line)]
    if not matched:
        matched = [0] if lines else []
    windows = []
    for n in matched[:24]:
        start = max(0, n - 3); end = min(len(lines), n + 5)
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(end, windows[-1][1]))
        else:
            windows.append((start, end))
    for start, end in windows:
        text = '\n'.join(lines[start:end])
        results.append({"path": path, "kind": "line_window", "symbol": "", "start_line": start+1,
                        "end_line": end, "text": text, "imports": "", "score": _score(query, '', text, path)})
    return results


def code_context(task: str, files: list[dict], token_budget: int = 1600, required_paths: list[str] | None = None) -> dict:
    _budget(token_budget); developer_intent(task); validate_files(files)
    required = set(required_paths or [])
    if not all(isinstance(p, str) for p in required) or not required.issubset({f['path'] for f in files}):
        raise ValueError("required_paths must reference caller-supplied file paths")
    query = terms(task)
    ranked: list[dict] = []
    for f in files:
        for candidate in _candidates(f['path'], f['content'], query):
            candidate['required'] = f['path'] in required
            ranked.append(candidate)
    ranked.sort(key=lambda c: (not c['required'], -c['score'], c['path'], c['start_line']))
    selected = []; selected_keys = set(); used = 0
    warnings = []
    for c in ranked:
        if not c['required'] and c['score'] <= 0 and selected:
            continue
        signature = (c['path'], c['start_line'], c['end_line'])
        if signature in selected_keys:
            continue
        import_lines = c['imports'] if (c['score'] > 0 or c['required']) and not any(
            item['path'] == c['path'] for item in selected) else ''
        snippet = f"# {c['path']}:{c['start_line']}-{c['end_line']} ({c['kind']})\n"
        if import_lines:
            snippet += '# Module context:\n' + import_lines + '\n'
        snippet += c['text']
        weight = estimate_text(snippet)
        if not c['required'] and used + weight > token_budget:
            continue
        selected.append({k: c[k] for k in ('path','kind','symbol','start_line','end_line')}
                        | {'text': snippet, 'required': c['required']})
        selected_keys.add(signature); used += weight
    # Preserve complete local and exact imported definitions, even when they
    # do not share task terms. Only caller-supplied Python files are considered.
    by_name = {(c['path'], c['symbol']): c for c in ranked if c['symbol']}
    module_paths: dict[str, set[str]] = {}
    for candidate in ranked:
        if candidate.get('module'):
            for alias in _module_aliases(candidate['path']):
                module_paths.setdefault(alias, set()).add(candidate['path'])
    by_module_name: dict[tuple[str, str], dict] = {}
    for candidate in ranked:
        if candidate.get('module') and candidate.get('symbol'):
            key = (candidate['module'], candidate['symbol'])
            if key not in by_module_name or candidate['start_line'] > by_module_name[key]['start_line']:
                by_module_name[key] = candidate
    pending = [(c['path'], c['symbol']) for c in selected if c['symbol']]
    explored = set()
    unresolved_dependencies: set[str] = set()
    while pending:
        entry = pending.pop(0)
        if entry in explored:
            continue
        explored.add(entry)
        cand = by_name.get(entry)
        if cand is None:
            continue
        dependencies = [(cand['path'], symbol, f"{cand['path']}:{symbol}", None)
                        for symbol in cand.get('dependencies', [])]
        for module, symbol in cand.get('dependency_refs', []):
            paths = module_paths.get(module, set())
            if len(paths) == 1:
                dependencies.append((next(iter(paths)), symbol, f"{module}.{symbol}", module))
            elif len(paths) > 1:
                unresolved_dependencies.add(f"{module}.{symbol}")
        for dependency_path, symbol, label, dependency_module in dependencies:
            dependency = by_name.get((dependency_path, symbol))
            if dependency is None and dependency_module:
                dependency = by_module_name.get((dependency_module, symbol))
            if dependency is None:
                if dependency_module:
                    unresolved_dependencies.add(label)
                continue
            signature = (dependency['path'], dependency['start_line'], dependency['end_line'])
            if signature in selected_keys:
                continue
            snippet = f"# dependency {dependency['path']}:{dependency['start_line']}-{dependency['end_line']}\n"
            if not any(item['path'] == dependency['path'] for item in selected) and dependency.get('imports'):
                snippet += '# Module context:\n' + dependency['imports'] + '\n'
            snippet += dependency['text']
            selected.append({k: dependency[k] for k in ('path','kind','symbol','start_line','end_line')}
                        | {'text': snippet, 'required': True})
            selected_keys.add(signature)
            used += estimate_text(snippet)
            pending.append((dependency['path'], dependency['symbol']))
            warnings.append(f"Preserved directly-called dependency: {label}")

    if not selected and ranked:
        # Better an explicit, over-budget excerpt than silently zero evidence.
        c = ranked[0]; snippet = f"# {c['path']}:{c['start_line']}-{c['end_line']}\n{c['text']}"
        selected = [{k: c[k] for k in ('path','kind','symbol','start_line','end_line')} | {'text': snippet, 'required': c['required']}]
        used = estimate_text(snippet)
        warnings.append('No complete code excerpt fitted budget; primary excerpt preserved beyond budget')
    if used > token_budget:
        warnings.append('Protected/complete code excerpts exceeded advisory budget')
    if unresolved_dependencies:
        warnings.extend(f"Dependency was not found in supplied files: {name}"
                        for name in sorted(unresolved_dependencies))
    chosen = {c['path'] for c in selected}
    context = '\n\n'.join(c['text'] for c in selected)
    return {'optimizer': 'code_context', 'intent': developer_intent(task), 'context': context,
            'selected_snippets': selected, 'selected_paths': sorted(chosen),
            'omitted_paths': [f['path'] for f in files if f['path'] not in chosen],
            'estimated_full_tokens': estimate_text('\n\n'.join(f"# {f['path']}\n{f['content']}" for f in files)),
            'estimated_optimized_tokens': estimate_text(context), 'budget_exceeded': estimate_text(context) > token_budget,
            'unresolved_dependencies': sorted(unresolved_dependencies),
            'warnings': warnings + ['Review dependencies and run tests before applying changes']}


def repository_retrieval(task: str, files: list[dict], token_budget: int = 1600,
                         required_paths: list[str] | None = None, max_files: int = 12) -> dict:
    _budget(token_budget); developer_intent(task); validate_files(files)
    if isinstance(max_files, bool) or not isinstance(max_files, int) or not 1 <= max_files <= 100:
        raise ValueError('max_files must be 1..100')
    required = set(required_paths or [])
    if not required.issubset({f['path'] for f in files}):
        raise ValueError('required_paths must reference caller-supplied file paths')
    query = terms(task)
    ranks = sorted(files, key=lambda f: (f['path'] not in required,
                   -_score(query, '', f['content'][:10000], f['path']), f['path']))
    selected = []; used = 0
    for f in ranks:
        need = estimate_text(f"# {f['path']}\n{f['content']}")
        is_required = f['path'] in required
        relevance = _score(query, '', f['content'][:10000], f['path'])
        if is_required or ((relevance > 0 or not selected) and len(selected) < max_files and used + need <= token_budget):
            selected.append(f); used += need
    if not selected and ranks:
        selected.append(ranks[0]); used = estimate_text(f"# {ranks[0]['path']}\n{ranks[0]['content']}")
    paths = {f['path'] for f in selected}
    return {'optimizer': 'repository_retrieval', 'selected_paths': [f['path'] for f in selected],
            'omitted_paths': [f['path'] for f in files if f['path'] not in paths],
            'selected_files': selected, 'estimated_full_tokens': sum(estimate_text(f"# {f['path']}\n{f['content']}") for f in files),
            'estimated_selected_tokens': used, 'budget_exceeded': used > token_budget,
            'warnings': (['Required files or fallback selection exceeded advisory budget'] if used > token_budget else [])
                        + ['Only authorized files were evaluated; retrieval is lexical, not semantic']}


def incremental_context(files: list[dict], previous_hashes: dict[str, str] | None = None,
                        prior_context_confirmed: bool = False) -> dict:
    validate_files(files)
    if not isinstance(prior_context_confirmed, bool):
        raise ValueError('prior_context_confirmed must be boolean')
    old = {} if previous_hashes is None else previous_hashes
    if not isinstance(old, dict) or len(old) > 100 or not all(isinstance(k, str) and isinstance(v, str) and re.fullmatch('[a-fA-F0-9]{64}', v) for k, v in old.items()):
        raise ValueError('previous_hashes must map paths to sha256 hex digests')
    digests = {f['path']: hashlib.sha256(f['content'].encode('utf-8')).hexdigest() for f in files}
    unchanged = [f['path'] for f in files if old.get(f['path']) == digests[f['path']]]
    skip = set(unchanged) if prior_context_confirmed else set()
    changed = [f for f in files if f['path'] not in skip]
    return {'optimizer':'incremental_context', 'selected_files': changed,
            'selected_paths':[f['path'] for f in changed], 'reused_paths':[f['path'] for f in files if f['path'] in skip],
            'unchanged_detected':unchanged, 'new_hashes':digests,
            'estimated_full_tokens':sum(estimate_text(f['content']) for f in files),
            'estimated_selected_tokens':sum(estimate_text(f['content']) for f in changed),
            'warnings':([] if prior_context_confirmed else ['Unconfirmed model context: unchanged files retained'])
                      + (['If model context was cleared or session changed, resend all referenced files'] if skip else [])}


def code_diff(diff: str, token_budget: int = 1600, context_lines: int = 2) -> dict:
    _budget(token_budget)
    if not isinstance(diff, str) or len(diff) > 300_000:
        raise ValueError('diff must be text of max 300000 chars')
    if isinstance(context_lines, bool) or not isinstance(context_lines, int) or not 0 <= context_lines <= 20:
        raise ValueError('context_lines must be from 0 to 20')
    lines = diff.splitlines(); selected = set()
    for i, line in enumerate(lines):
        if line.startswith(('diff --git ', 'index ', '--- ', '+++ ', '@@ ', 'old mode ', 'new mode ',
                            'new file mode', 'deleted file mode', 'similarity index ', 'dissimilarity index ',
                            'rename from ', 'rename to ', 'copy from ', 'copy to ', 'Binary files ',
                            '\\ No newline at end of file')):
            selected.add(i)
        if line.startswith(('+', '-')):
            selected.add(i)
            for k in range(max(0,i-context_lines), min(len(lines), i+context_lines+1)):
                if lines[k].startswith(' '):
                    selected.add(k)
    if not selected and lines:
        selected = set(range(len(lines)))
    out = diff if 'GIT binary patch' in lines else '\n'.join(lines[i] for i in sorted(selected))
    estimated = estimate_text(out)
    condensed = out.strip('\n') != diff.strip('\n')
    return {'optimizer':'code_diff', 'context':out, 'changes_preserved':all(
        not s.startswith(('+', '-')) or i in selected
        for i,s in enumerate(lines)), 'estimated_full_tokens':estimate_text(diff),
        'estimated_optimized_tokens':estimated, 'budget_exceeded':estimated > token_budget,
        'analysis_only_not_applyable_patch':condensed,
        'warnings':(['Changed lines exceeded advisory budget; they were preserved'] if estimated > token_budget else [])
                    + (['Condensed excerpts are for code review, NOT for git apply or replacing source patches']
                       if condensed else [])}


def _diagnostic_lines(log: str, token_budget: int, kind: str) -> dict:
    _budget(token_budget)
    if not isinstance(log, str) or len(log) > 500_000:
        raise ValueError('log must be text of max 500000 chars')
    lines=log.splitlines()
    critical=[i for i,line in enumerate(lines) if _ERRORS.search(line) or _TRACE.search(line)
              or line.strip().startswith(('E ', 'FAILED ', 'FAIL ', '== FAILURES =='))]
    # Only discard unambiguously successful test-result lines. All other lines,
    # including entire tracebacks and multiline assertions, remain untouched.
    passed = re.compile(r'^\s*(?:TEST\s+\S+|\S+::\S+|test_[A-Za-z0-9_]+:?)\s+PASSED(?:\s+\[[^\]]+\])?\s*$')
    start = 0
    if kind == 'test_log':
        while start < len(lines) and passed.fullmatch(lines[start]) and not _ERRORS.search(lines[start]):
            start += 1
    result = lines[start:]
    out = '\n'.join(result)
    return {'optimizer':kind,'context':out,'diagnostic_lines':len(critical),
            'estimated_full_tokens':estimate_text(log),'estimated_optimized_tokens':estimate_text(out),
            'budget_exceeded':estimate_text(out)>token_budget,
            'warnings':(['All detected failure evidence preserved despite budget'] if estimate_text(out)>token_budget else [])
                      + (['No explicit failure markers found; unrecognized diagnostic lines preserved'] if not critical and lines else [])
                      + (['Verify the full original diagnostics'] if out.strip('\n') != log.strip('\n') else [])}


def test_log(log: str, token_budget: int = 1600) -> dict:
    return _diagnostic_lines(log,token_budget,'test_log')


def _compact_repeated_error_lines(log: str) -> str:
    # keepends: never normalize CRLF or drop the final newline; a log without
    # repeated non-critical lines must come back byte-identical.
    lines = log.splitlines(keepends=True)
    compacted: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        text = line.rstrip("\r\n")
        end = index + 1
        while end < len(lines) and lines[end].rstrip("\r\n") == text:
            end += 1
        count = end - index
        critical = (_ERRORS.search(text) or _TRACE.search(text) or
                    text.strip().startswith(("Traceback ", "During handling of the above", "The above exception")))
        if count > 1 and text.strip() and not critical:
            newline = line[len(text):] or "\n"
            last = lines[end - 1][len(text):]
            compacted.extend((text + newline, f"[ATOF: repeated {count} identical diagnostic lines]" + last))
        else:
            compacted.extend(lines[index:end])
        index = end
    return "".join(compacted)


_PY_FRAME = re.compile(r'^\s+File "([^"]+)", line \d+')
_AT_FRAME = re.compile(r"^\s+at (?:async )?(\S.*)$")
_LIBRARY_FRAME = re.compile(
    r"site-packages|dist-packages|[\\/]Lib[\\/]|[\\/]lib[\\/]python\d|<frozen |node_modules|node:internal|"
    r"^(?:java|javax|jdk|sun|kotlin|scala|org\.springframework|org\.apache|org\.junit|io\.netty|"
    r"reactor|com\.sun)\.|^internal/|[\\/]\.cargo[\\/]registry|[\\/]rustc[\\/]|[\\/]go[\\/]src[\\/]runtime")
_MIN_FOLDED_FRAMES = 4


def _frames(lines: list[str]) -> list[tuple[int, int, bool]]:
    """(start, end, is_library) per stack frame; a Python frame includes its code line."""
    frames, index = [], 0
    while index < len(lines):
        text = lines[index].rstrip("\r\n")
        python = _PY_FRAME.match(text)
        other = None if python else _AT_FRAME.match(text)
        if not python and not other:
            index += 1
            continue
        end = index + 1
        if python and end < len(lines):
            follower = lines[end].rstrip("\r\n")
            indent = len(text) - len(text.lstrip())
            if (follower.strip() and len(follower) - len(follower.lstrip()) > indent
                    and not _PY_FRAME.match(follower)):
                end += 1
        location = python.group(1) if python else other.group(1)
        frames.append((index, end, bool(_LIBRARY_FRAME.search(location))))
        index = end
    return frames


def fold_library_frames(log: str) -> str:
    """Fold long runs of framework/library stack frames; keep the first and last of each run.

    Exception lines, user frames, chained-exception markers and every other line
    are preserved byte-for-byte (including CRLF). A log without such runs is
    returned unchanged.
    """
    lines = log.splitlines(keepends=True)
    frames = _frames(lines)
    drop: dict[int, tuple[int, int]] = {}
    run: list[tuple[int, int, bool]] = []

    def flush() -> None:
        if len(run) >= _MIN_FOLDED_FRAMES:
            first_omitted, last_omitted = run[1][0], run[-2][1]
            drop[first_omitted] = (last_omitted, len(run) - 2)
        run.clear()

    for frame in frames:
        contiguous = run and frame[0] == run[-1][1]
        if frame[2] and (not run or contiguous):
            run.append(frame)
            continue
        flush()
        if frame[2]:
            run.append(frame)
    flush()
    if not drop:
        return log
    out, index = [], 0
    while index < len(lines):
        if index in drop:
            end, count = drop[index]
            sample = lines[index]
            indent = sample[:len(sample) - len(sample.lstrip())]
            ending = sample[len(sample.rstrip("\r\n")):] or "\n"
            out.append(f"{indent}[ATOF: {count} library frames omitted]{ending}")
            index = end
            continue
        out.append(lines[index])
        index += 1
    folded = "".join(out)
    kept = [line.rstrip("\r\n") for line in folded.splitlines()]
    for line in lines:
        text = line.rstrip("\r\n")
        frame = _PY_FRAME.match(text) or _AT_FRAME.match(text)
        if (not frame and text.strip() and not text.startswith((" ", "\t"))) and text not in kept:
            return log  # an exception/diagnostic line went missing: fail closed
    return folded


def _fold_repeated_tracebacks(log: str) -> str:
    """Replace later byte-identical traceback blocks with a reference to the first."""
    lines = log.splitlines(keepends=True)
    blocks, index = [], 0
    while index < len(lines):
        if lines[index].startswith("Traceback (most recent call last):"):
            end = index + 1
            while end < len(lines) and lines[end].startswith((" ", "\t")):
                end += 1
            if end < len(lines) and lines[end].strip():
                end += 1
            blocks.append((index, end))
            index = end
        else:
            index += 1
    seen: dict[str, int] = {}
    replace: dict[int, tuple[int, int]] = {}
    for number, (start, end) in enumerate(blocks):
        key = "".join(line.rstrip("\r\n") + "\n" for line in lines[start:end])
        if key in seen and end - start >= 4:
            replace[start] = (end, seen[key])
        else:
            seen.setdefault(key, number + 1)
    if not replace:
        return log
    out, index = [], 0
    while index < len(lines):
        if index in replace:
            end, first = replace[index]
            ending = lines[end - 1][len(lines[end - 1].rstrip("\r\n")):] or "\n"
            exception = lines[end - 1].rstrip("\r\n")
            out.append(f"[ATOF: traceback identical to traceback #{first} above]{ending}{exception}{ending}")
            index = end
            continue
        out.append(lines[index])
        index += 1
    return "".join(out)


def compact_error_log(log: str) -> str:
    """BLM-7 repeated-line folding plus traceback-aware frame and duplicate folding."""
    return _compact_repeated_error_lines(fold_library_frames(_fold_repeated_tracebacks(log)))


def error_context(log: str, token_budget: int = 1600, files: list[dict] | None = None) -> dict:
    out=_diagnostic_lines(log,token_budget,'error_context')
    # Public API keeps its normalized line form; the Responses gateway uses the
    # byte-preserving _compact_repeated_error_lines result directly.
    folded = compact_error_log(log)
    compacted = "\n".join(folded.splitlines())
    out['context'] = compacted
    out['estimated_optimized_tokens'] = estimate_text(compacted)
    out['budget_exceeded'] = out['estimated_optimized_tokens'] > token_budget
    if folded != log:
        out['warnings'].append('Repeated identical non-critical diagnostic lines, duplicate tracebacks or long library-frame runs were folded; exception lines and application frames are retained')
        if 'Verify the full original diagnostics' not in out['warnings']:
            out['warnings'].append('Verify the full original diagnostics')
    validate_files(files or [])
    cited=[]
    # Exact path/basename correlation only. No repository file reads.
    for f in files or []:
        path=f['path']; basename=path.replace('\\','/').split('/')[-1]
        if path in log or (len(basename)>=4 and basename in log):
            cited.append(path)
    out['referenced_paths']=cited
    return out


def coding_context(task: str, files: list[dict], diff: str = '', test_output: str = '',
                   error_output: str = '') -> str:
    """Canonical full-evidence baseline, including the same framing as selected evidence."""
    segments = []
    if files:
        segments.append('SOURCE EXCERPTS (untrusted evidence):\n' +
                        '\n\n'.join(f"# {f['path']}\n{f['content']}" for f in files))
    for label, text in (('GIT DIFF (analysis only)', diff), ('TEST DIAGNOSTICS', test_output),
                        ('ERROR DIAGNOSTICS', error_output)):
        if text:
            segments.append(label + ':\n' + text)
    return 'TASK (preserve exactly):\n' + task + ('\n\n' + '\n\n'.join(segments) if segments else '')


def optimize_coding(task: str, files: list[dict] | None = None, diff: str = '', test_output: str = '',
                    error_output: str = '', token_budget: int = 3200,
                    previous_hashes: dict[str, str] | None = None, prior_context_confirmed: bool = False,
                    required_paths: list[str] | None = None) -> dict:
    _budget(token_budget); intent=developer_intent(task); files=validate_files([] if files is None else files)
    if required_paths is not None and (not isinstance(required_paths, list) or
            any(not isinstance(path, str) for path in required_paths) or
            not set(required_paths).issubset({f['path'] for f in files})):
        raise ValueError('required_paths must reference caller-supplied file paths')
    if not all(isinstance(x,str) for x in (diff,test_output,error_output)):
        raise ValueError('diff, test_output and error_output must be text')
    if not files:
        incremental_context([], previous_hashes, prior_context_confirmed)
    enabled = int(bool(files)) + int(bool(diff)) + int(bool(test_output)) + int(bool(error_output))
    share = max(64, token_budget // max(1, enabled))
    outputs={}; segments=[]; warnings=[]
    decisions = {}

    def run(name, function, reason, *args, **kwargs):
        started = time.perf_counter()
        value = function(*args, **kwargs)
        decisions[name] = {
            'optimizer': name, 'status': 'activated', 'reason': reason,
            'estimated_tokens_before': value.get('estimated_full_tokens'),
            'estimated_tokens_after': value.get('estimated_optimized_tokens', value.get('estimated_selected_tokens')),
            'latency_ms': round((time.perf_counter() - started) * 1000, 3),
            'input_evidence': ('source_files' if name in {
                'code_context', 'repository_retrieval', 'incremental_context'} else name),
            'output_ref': f'details.{name}',
            'delivered_to_model': False,
        }
        return value

    def skip(name, reason):
        decisions[name] = {'optimizer': name, 'status': 'skipped', 'reason': reason,
                           'estimated_tokens_before': None, 'estimated_tokens_after': None,
                           'latency_ms': 0.0, 'input_evidence': 'absent', 'output_ref': None,
                           'delivered_to_model': False}

    def preserve_if_expanded(name, value, original):
        if value['estimated_optimized_tokens'] > value['estimated_full_tokens']:
            value['context'] = original
            value['estimated_optimized_tokens'] = value['estimated_full_tokens']
            value['budget_exceeded'] = value['estimated_full_tokens'] > share
            decisions[name].update(status='bypassed', reason='stage_expansion',
                                   estimated_tokens_after=value['estimated_full_tokens'])
            value['warnings'].append('Original evidence retained because optimization expanded it')

    for name, function, text, reason, absent, label in (
        ('code_diff', code_diff, diff, 'diff_provided', 'no_diff', 'GIT DIFF (analysis only)'),
        ('test_log', test_log, test_output, 'test_output_provided', 'no_test_output', 'TEST DIAGNOSTICS'),
        ('error_context', error_context, error_output, 'error_output_provided', 'no_error_output', 'ERROR DIAGNOSTICS'),
    ):
        if not text:
            skip(name, absent)
            continue
        value = run(name, function, reason, text, share, **({'files': files} if name == 'error_context' else {}))
        outputs[name] = value
        preserve_if_expanded(name, value, text)
        segments.append(label + ':\n' + value['context'])
        warnings.extend(value['warnings'])
    # Allocate only after diagnostic compaction, not from the uncompressed log size.
    source_budget = max(64, token_budget - estimate_text(task) -
                        sum(estimate_text(segment) for segment in segments) - 64)

    if files:
        if previous_hashes is not None and not isinstance(previous_hashes, dict):
            raise ValueError('previous_hashes must map paths to sha256 hex digests')
        if previous_hashes:
            incremental=run('incremental_context', incremental_context,
                            'confirmed_prior_context' if prior_context_confirmed else 'unconfirmed_prior_context',
                            files, previous_hashes, prior_context_confirmed)
            current=incremental['selected_files']
            outputs['incremental_context']=incremental
            warnings.extend(incremental['warnings'])
        else:
            # Validate the explicit confirmation even when hashes are absent.
            if not isinstance(prior_context_confirmed, bool):
                raise ValueError('prior_context_confirmed must be boolean')
            current=files
            skip('incremental_context', 'no_previous_hashes')
        if current:
            repo=run('repository_retrieval', repository_retrieval, 'source_files_available',
                     task,current,source_budget, required_paths=[p for p in (required_paths or []) if p in {f['path'] for f in current}])
            outputs['repository_retrieval']={k:v for k,v in repo.items() if k!='selected_files'}
            code=run('code_context', code_context, 'source_files_available',
                     task,repo['selected_files'],source_budget,required_paths=[p for p in (required_paths or []) if p in repo['selected_paths']])
            if code['estimated_optimized_tokens'] > code['estimated_full_tokens']:
                original = '\n\n'.join(f"# {f['path']}\n{f['content']}" for f in repo['selected_files'])
                original_tokens = estimate_text(original)
                if original_tokens <= code['estimated_optimized_tokens']:
                    code['context'] = original
                    code['selected_paths'] = [f['path'] for f in repo['selected_files']]
                    code['omitted_paths'] = []
                    code['estimated_optimized_tokens'] = original_tokens
                    code['budget_exceeded'] = original_tokens > share
                    code['warnings'].append('Expanded excerpts bypassed; full selected files retained')
                    decisions['code_context'].update(status='bypassed', reason='stage_expansion',
                                                     estimated_tokens_after=original_tokens)
            outputs['code_context']={k:v for k,v in code.items() if k!='selected_snippets'}
            if code['context']:
                segments.insert(0, 'SOURCE EXCERPTS (untrusted evidence):\n'+code['context'])
            warnings.extend(code['warnings']+repo['warnings'])
        else:
            skip('repository_retrieval', 'no_current_files')
            skip('code_context', 'no_current_files')
    else:
        for name in ('incremental_context', 'repository_retrieval', 'code_context'):
            skip(name, 'no_source_files')
    context='TASK (preserve exactly):\n'+task+('\n\n'+'\n\n'.join(segments) if segments else '')
    original = coding_context(task, files, diff, test_output, error_output)
    full = estimate_text(original)
    mode = 'optimized'
    if estimate_text(context) >= full:
        context = original
        mode = 'bypass'
        warnings.append('No net reduction including framing; original evidence retained')
    if estimate_text(context) > token_budget:
        mode = 'budget_exceeded'
        warnings.append('Protected evidence cannot fit the budget; do not deliver this request automatically')
    if mode != 'optimized':
        for decision in decisions.values():
            if decision['status'] == 'activated':
                decision.update(status='bypassed', reason='budget_exceeded' if mode == 'budget_exceeded' else 'overall_bypass')
    for decision in decisions.values():
        before, after = decision['estimated_tokens_before'], decision['estimated_tokens_after']
        decision['estimated_tokens_saved'] = (
            before - after if before is not None and after is not None and decision['status'] == 'activated' else 0)
    evidence = [name for name, present in (
        ('source_files', bool(files)), ('diff', bool(diff)),
        ('test_output', bool(test_output)), ('error_output', bool(error_output)),
        ('verified_prior_context', bool(previous_hashes) and prior_context_confirmed),
    ) if present]
    return {'mode': mode, 'intent':intent, 'intent_routing': route_intent(task, evidence_types=evidence), 'context':context,
            'active_optimizers':[name for name, decision in decisions.items() if decision['status'] == 'activated'], 'details':outputs,
            'optimizer_decisions': list(decisions.values()),
            'estimated_full_tokens':full,'estimated_optimized_tokens':estimate_text(context),
            'estimated_reduction_pct':round(100*(full-estimate_text(context))/full,2) if full and mode == 'optimized' else 0,
            'token_budget':token_budget,'budget_exceeded':estimate_text(context)>token_budget,
            'warnings':sorted(set(warnings + (['Combined context exceeded advisory budget; critical evidence retained'] if estimate_text(context)>token_budget else []))),
            'token_counts_are_estimates':True,'real_model_quality_evaluated':False}
