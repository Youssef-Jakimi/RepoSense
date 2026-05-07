"""
Static analysis: untested function detection and high-fan-out breaking-point detection.

Uses Python `ast` for .py files; regex for all other supported languages.
Never executes code from the analyzed repo and never calls IBM Bob.
"""

import ast
import os
import re

from intelligence.context_builder import COMMON_NAME_STOPLIST

# ---------------------------------------------------------------------------
# Module-level compiled regexes
# ---------------------------------------------------------------------------

_RE_JS_FUNC  = re.compile(r'\b(?:function|async\s+function)\s+(\w+)')
_RE_JS_CLASS = re.compile(r'\bclass\s+(\w+)')
_RE_JS_ARROW = re.compile(r'\bconst\s+(\w+)\s*=\s*(?:async\s*)?\(')

_RE_GO_FUNC   = re.compile(r'\bfunc\s+(?:\([^)]*\)\s*)?(\w+)\b')

_RE_JAVA_FUNC = re.compile(
    r'\b(?:public|private|protected|static|final|fun|def)\s+[\w<>,\s\[\]]*\s+(\w+)\s*\('
)

_RE_C_FUNC  = re.compile(r'^\s*[\w*\s]+\b(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE)
_RE_RUBY_FUNC = re.compile(r'\bdef\s+(\w+)')
_RE_RUST_FUNC = re.compile(r'\bfn\s+(\w+)')
_RE_PHP_FUNC  = re.compile(r'\bfunction\s+(\w+)')

# Python regex fallback: matches `def`, `async def`, or `class` at start of a line
_RE_PY_FALLBACK = re.compile(
    r'^\s*(?:async\s+)?def\s+(\w+)|^\s*class\s+(\w+)', re.MULTILINE
)

_STOPLIST: set[str] = set(COMMON_NAME_STOPLIST)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    path_norm = path.replace("\\", "/")
    basename  = path_norm.split("/")[-1].lower()
    stem      = basename.rsplit(".", 1)[0] if "." in basename else basename
    path_lower = path_norm.lower()

    # Rule 1: test_ prefix or _test suffix in the basename stem
    if "test_" in basename or "_test" in stem:
        return True

    # Rule 2: directory component is test / tests / __tests__ / spec
    segments = path_lower.split("/")
    if any(seg in {"test", "tests", "__tests__", "spec"} for seg in segments[:-1]):
        return True

    # Rule 3: JS/TS test-specific extensions
    if any(basename.endswith(ext) for ext in (".test.js", ".test.ts", ".spec.js", ".spec.ts")):
        return True

    return False


def _get_lang_group(file: dict) -> str | None:
    """Canonical language identifier used for regex dispatch."""
    lang = (file.get("language") or "").lower().strip()
    ext  = os.path.splitext(file.get("path", ""))[1].lower()

    if lang == "python"                         or ext == ".py":   return "python"
    if lang in ("javascript", "js")             or ext == ".js":   return "javascript"
    if lang in ("typescript", "ts")             or ext == ".ts":   return "typescript"
    if lang == "go"                             or ext == ".go":   return "go"
    if lang == "java"                           or ext == ".java": return "java"
    if lang == "kotlin"                         or ext == ".kt":   return "kotlin"
    if lang == "scala"                          or ext == ".scala":return "scala"
    if lang == "swift"                          or ext == ".swift":return "swift"
    if lang in ("c#", "csharp")                 or ext == ".cs":   return "csharp"
    if lang in ("c", "c++", "cpp") or ext in (".c", ".cpp", ".cc", ".h", ".hpp"): return "c"
    if lang == "ruby"                           or ext == ".rb":   return "ruby"
    if lang == "rust"                           or ext == ".rs":   return "rust"
    if lang == "php"                            or ext == ".php":  return "php"
    return None


def _line_of(content: str, match_start: int) -> int:
    return content[:match_start].count("\n") + 1


def _extract_regex_names(content: str, lang_group: str) -> list[tuple[str, int]]:
    """Return deduplicated (name, lineno) pairs for the given language group."""
    results: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()

    def _add(name: str, start: int) -> None:
        key = (name, _line_of(content, start))
        if key not in seen:
            seen.add(key)
            results.append(key)

    if lang_group in ("javascript", "typescript"):
        for m in _RE_JS_FUNC.finditer(content):
            _add(m.group(1), m.start())
        for m in _RE_JS_CLASS.finditer(content):
            _add(m.group(1), m.start())
        for m in _RE_JS_ARROW.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group == "go":
        for m in _RE_GO_FUNC.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group in ("java", "kotlin", "scala", "swift", "csharp"):
        for m in _RE_JAVA_FUNC.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group == "c":
        for m in _RE_C_FUNC.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group == "ruby":
        for m in _RE_RUBY_FUNC.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group == "rust":
        for m in _RE_RUST_FUNC.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group == "php":
        for m in _RE_PHP_FUNC.finditer(content):
            _add(m.group(1), m.start())

    elif lang_group == "python":
        for m in _RE_PY_FALLBACK.finditer(content):
            name = m.group(1) or m.group(2)
            _add(name, m.start())

    return results


def _detect_functions_in_file(file: dict) -> tuple[list[dict], bool]:
    """
    Returns (functions, best_effort).
    best_effort=True when regex was used instead of AST.
    """
    path       = file.get("path", "")
    content    = file.get("content", "")
    lang_group = _get_lang_group(file)

    if not content or lang_group is None:
        return [], False

    if lang_group == "python":
        try:
            tree = ast.parse(content)
            funcs = [
                {
                    "name": node.name,
                    "path": path,
                    "line": node.lineno,
                    "language": "python",
                    "detection_method": "ast",
                }
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]
            return funcs, False
        except SyntaxError:
            names = _extract_regex_names(content, "python")
            funcs = [
                {
                    "name": name,
                    "path": path,
                    "line": line,
                    "language": "python",
                    "detection_method": "regex-fallback",
                }
                for name, line in names
            ]
            return funcs, True

    else:
        names = _extract_regex_names(content, lang_group)
        funcs = [
            {
                "name": name,
                "path": path,
                "line": line,
                "language": lang_group,
                "detection_method": "regex",
            }
            for name, line in names
        ]
        return funcs, True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_repo(files: list[dict]) -> dict:
    """
    Args:
        files: list of {path, content, language, size} from github_loader

    Returns:
        {
            "total_functions": int,
            "tested_functions": int,
            "untested_functions": list[dict],   # [{name, path, line, language, detection_method}]
            "breaking_points": list[dict],      # [{name, path, line, language, fan_out, referenced_in: list[str]}]
            "no_tests_detected": bool,
            "no_functions_detected": bool,
            "language_breakdown": dict[str, dict],  # {lang: {functions, tested, best_effort}}
        }
    """
    valid_files  = [f for f in files if f.get("content")]
    test_files   = [f for f in valid_files if _is_test_file(f["path"])]
    source_files = [f for f in valid_files if not _is_test_file(f["path"])]

    no_tests_detected = len(test_files) == 0

    # -----------------------------------------------------------------------
    # Step A — detect functions in source files
    # -----------------------------------------------------------------------
    all_funcs: list[dict]       = []
    lang_best_effort: dict[str, bool] = {}

    for file in source_files:
        funcs, best_effort = _detect_functions_in_file(file)
        all_funcs.extend(funcs)
        lang_group = _get_lang_group(file)
        if lang_group is not None:
            lang_best_effort[lang_group] = (
                lang_best_effort.get(lang_group, False) or best_effort
            )

    total_functions     = len(all_funcs)
    no_functions_detected = total_functions == 0

    if no_functions_detected:
        return {
            "total_functions":      0,
            "tested_functions":     0,
            "untested_functions":   [],
            "breaking_points":      [],
            "no_tests_detected":    no_tests_detected,
            "no_functions_detected": True,
            "language_breakdown":   {},
        }

    # -----------------------------------------------------------------------
    # Indices used by both untested and breaking-point detection
    # -----------------------------------------------------------------------
    test_contents: list[str]      = [f["content"] for f in test_files]
    source_map:    dict[str, str] = {f["path"]: f["content"] for f in source_files}

    # -----------------------------------------------------------------------
    # Apply stoplist filter (name length < 3 or common stopword)
    # Spec verification requires `foo` (len=3) to count as tested, so the
    # threshold is strictly < 3, not <= 3.
    # -----------------------------------------------------------------------
    filtered_funcs = [
        f for f in all_funcs
        if len(f["name"]) >= 3 and f["name"].lower() not in _STOPLIST
    ]

    # -----------------------------------------------------------------------
    # Step C — tested / untested classification
    # Cache results by name: if a name appears in any test file it is tested.
    # -----------------------------------------------------------------------
    _tested_cache: dict[str, bool] = {}

    def _is_name_tested(name: str) -> bool:
        if name not in _tested_cache:
            pat = re.compile(rf"\b{re.escape(name)}\b")
            _tested_cache[name] = any(pat.search(c) for c in test_contents)
        return _tested_cache[name]

    untested_funcs: list[dict] = [f for f in filtered_funcs if not _is_name_tested(f["name"])]
    tested_count   = len(filtered_funcs) - len(untested_funcs)

    # -----------------------------------------------------------------------
    # Step D — breaking points (fan_out >= 5 in non-test source files)
    # -----------------------------------------------------------------------
    breaking_points: list[dict] = []
    for func in filtered_funcs:
        name = func["name"]
        pat  = re.compile(rf"\b{re.escape(name)}\b")
        refs = [
            path for path, content in source_map.items()
            if path != func["path"] and pat.search(content)
        ]
        if len(refs) >= 5:
            breaking_points.append({
                "name":          func["name"],
                "path":          func["path"],
                "line":          func["line"],
                "language":      func["language"],
                "fan_out":       len(refs),
                "referenced_in": refs[:10],
            })

    # -----------------------------------------------------------------------
    # Sort and truncate
    # -----------------------------------------------------------------------
    untested_funcs.sort(key=lambda f: (f["path"], f["line"]))
    untested_funcs = untested_funcs[:50]

    breaking_points.sort(key=lambda f: -f["fan_out"])
    breaking_points = breaking_points[:20]

    # -----------------------------------------------------------------------
    # Step F — language breakdown
    # `functions` counts all detected (before stoplist filter).
    # `tested` counts filtered functions whose name appears in a test file.
    # -----------------------------------------------------------------------
    lang_func_count:   dict[str, int] = {}
    lang_tested_count: dict[str, int] = {}

    for func in all_funcs:
        lang = func["language"]
        lang_func_count[lang] = lang_func_count.get(lang, 0) + 1

    for func in filtered_funcs:
        lang = func["language"]
        if _is_name_tested(func["name"]):
            lang_tested_count[lang] = lang_tested_count.get(lang, 0) + 1

    language_breakdown = {
        lang: {
            "functions":  count,
            "tested":     lang_tested_count.get(lang, 0),
            "best_effort": lang_best_effort.get(lang, True),
        }
        for lang, count in lang_func_count.items()
    }

    return {
        "total_functions":       total_functions,
        "tested_functions":      tested_count,
        "untested_functions":    untested_funcs,
        "breaking_points":       breaking_points,
        "no_tests_detected":     no_tests_detected,
        "no_functions_detected": False,
        "language_breakdown":    language_breakdown,
    }


# ---------------------------------------------------------------------------
# Verification (run directly: python -m review.risk_analyzer)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pprint

    # --- Test 1: one source function, one test file that references it ------
    synthetic = [
        {
            "path": "app.py",
            "content": "def foo():\n    pass\n",
            "language": "python",
            "size": 25,
        },
        {
            "path": "test_app.py",
            "content": "from app import foo\nfoo()\n",
            "language": "python",
            "size": 30,
        },
    ]
    r1 = analyze_repo(synthetic)
    assert r1["total_functions"]  == 1,  f"total_functions: {r1['total_functions']}"
    assert r1["tested_functions"] == 1,  f"tested_functions: {r1['tested_functions']}"
    assert r1["no_tests_detected"]    is False
    assert r1["no_functions_detected"] is False
    assert r1["untested_functions"] == []
    print("Test 1 PASSED — tested_functions=1")

    # --- Test 2: no test files → no_tests_detected=True --------------------
    r2 = analyze_repo([
        {"path": "app.py", "content": "def foo():\n    pass\n", "language": "python", "size": 25},
    ])
    assert r2["no_tests_detected"]    is True,  "Expected no_tests_detected=True"
    assert r2["tested_functions"]     == 0,     f"tested_functions: {r2['tested_functions']}"
    assert r2["total_functions"]      == 1
    assert len(r2["untested_functions"]) == 1
    print("Test 2 PASSED — no_tests_detected=True")

    # --- Test 3: empty file list --------------------------------------------
    r3 = analyze_repo([])
    assert r3["no_functions_detected"] is True
    assert r3["no_tests_detected"]     is True
    assert r3["total_functions"]       == 0
    print("Test 3 PASSED — empty file list handled")

    # --- Test 4: breaking point detection -----------------------------------
    shared_func = "authenticate"
    callers = [
        {"path": f"svc{i}.py", "content": f"from auth import {shared_func}\n{shared_func}(token)\n",
         "language": "python", "size": 50}
        for i in range(6)
    ]
    definer = {"path": "auth.py", "content": f"def {shared_func}(token):\n    pass\n",
               "language": "python", "size": 40}
    r4 = analyze_repo([definer] + callers)
    assert len(r4["breaking_points"]) == 1, f"breaking_points: {r4['breaking_points']}"
    bp = r4["breaking_points"][0]
    assert bp["name"]    == shared_func
    assert bp["fan_out"] == 6
    print(f"Test 4 PASSED — breaking_point '{shared_func}' fan_out={bp['fan_out']}")

    print("\nAll verification tests PASSED.")
    print("\n--- Sample output (Test 4) ---")
    pprint.pprint(r4)
