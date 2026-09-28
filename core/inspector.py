"""
HEUSC — The Inspector.
100% deterministic rule-based static analysis.
No LLM calls. Measures cyclomatic complexity, code smells, function length,
security risks (SQLi, dangerous evals, swallowed errors), and duplication.
Supports scanning local paths or cloning public GitHub repositories.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any, Tuple, Optional


class ASTCodeAuditor(ast.NodeVisitor):
    """AST visitor to detect security issues, code smells, and long functions."""

    def __init__(self, filename: str, rel_path: str, lines: List[str]):
        self.filename = filename
        self.rel_path = rel_path
        self.lines = lines
        self.issues = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 1. Function Length Check
        line_count = (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') and node.end_lineno else len(node.body)
        if line_count > 30:
            self.issues.append({
                "function": node.name,
                "issue": "excessive_function_length",
                "detail": f"Function spans {line_count} lines (threshold is 30). Violates single responsibility.",
                "metric": f"{line_count} lines",
                "severity": "medium" if line_count < 60 else "high",
            })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)  # Treat async functions similarly

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # 2. Dangerous calls (eval, exec, os.system)
        if func_name in ("eval", "exec"):
            self.issues.append({
                "function": getattr(node, "_parent_func", "module_scope"),
                "issue": "dangerous_dynamic_execution",
                "detail": f"Direct call to '{func_name}' allows arbitrary code execution.",
                "metric": None,
                "severity": "high",
            })
        elif func_name == "system" and isinstance(node.func, ast.Attribute):
            self.issues.append({
                "function": getattr(node, "_parent_func", "module_scope"),
                "issue": "arbitrary_command_execution",
                "detail": "os.system() call detected. Vulnerable to command injection.",
                "metric": None,
                "severity": "high",
            })

        # 3. SQL Injection risk via string formatting in cursor/execute calls
        if func_name in ("execute", "executemany", "raw_query", "query", "run_query"):
            if node.args:
                first_arg = node.args[0]
                # Pattern: execute(f"SELECT ... {var}")
                if isinstance(first_arg, ast.JoinedStr):
                    self.issues.append({
                        "function": getattr(node, "_parent_func", "unknown"),
                        "issue": "sql_injection_risk",
                        "detail": "SQL query formed using interpolated f-string in query execution.",
                        "metric": None,
                        "severity": "high",
                    })
                # Pattern: execute("SELECT ... %s" % var) or execute("...".format(var))
                elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, ast.Mod):
                    self.issues.append({
                        "function": getattr(node, "_parent_func", "unknown"),
                        "issue": "sql_injection_risk",
                        "detail": "SQL query constructed via % string formatting operator.",
                        "metric": None,
                        "severity": "high",
                    })
                elif isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Attribute) and first_arg.func.attr == "format":
                    self.issues.append({
                        "function": getattr(node, "_parent_func", "unknown"),
                        "issue": "sql_injection_risk",
                        "detail": "SQL query constructed via str.format() instead of parameterized placeholders.",
                        "metric": None,
                        "severity": "high",
                    })

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        # 4. Swallowed exceptions (except: pass or except Exception: pass)
        for handler in node.handlers:
            if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                exc_type = "bare except" if handler.type is None else getattr(handler.type, 'id', 'Exception')
                self.issues.append({
                    "function": getattr(node, "_parent_func", "unknown"),
                    "issue": "swallowed_exception",
                    "detail": f"Silent failure: catch-all '{exc_type}: pass' completely swallows errors.",
                    "metric": None,
                    "severity": "medium",
                })
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # 5. Hardcoded credentials / secret keys
        for target in node.targets:
            if isinstance(target, ast.Name):
                name_upper = target.id.upper()
                if any(k in name_upper for k in ("API_KEY", "SECRET_KEY", "PASSWORD", "AUTH_TOKEN")):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        if len(val) > 6 and not val.startswith("your_"):
                            self.issues.append({
                                "function": "module_scope",
                                "issue": "hardcoded_secret",
                                "detail": f"Apparent hardcoded secret '{target.id}' assigned directly in source.",
                                "metric": None,
                                "severity": "high",
                            })
        self.generic_visit(node)


def tag_parent_functions(tree: ast.AST):
    """Tag AST nodes with their enclosing function name for accurate reporting."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                setattr(child, "_parent_func", node.name)
            elif hasattr(node, "_parent_func"):
                setattr(child, "_parent_func", node._parent_func)


def compute_radon_complexity(file_path: str, code: str) -> List[Dict[str, Any]]:
    """Runs radon cyclomatic complexity analysis if available."""
    findings = []
    try:
        from radon.complexity import cc_visit
        blocks = cc_visit(code)
        for b in blocks:
            # Complexity >= 7 or rank C/D/E/F
            if b.complexity >= 8:
                severity = "high" if b.complexity >= 12 else "medium"
                findings.append({
                    "function": b.name,
                    "issue": "high_cyclomatic_complexity",
                    "detail": f"Cyclomatic complexity score of {b.complexity} (Grade {b.letter_rank}). Highly branched logic.",
                    "metric": f"CC: {b.complexity} (Rank {b.letter_rank})",
                    "severity": severity,
                })
    except ImportError:
        # Fallback if radon is not yet installed in active env
        pass
    except Exception:
        pass
    return findings


def detect_code_duplication(file_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Detects duplicated code blocks across repository files."""
    findings = []
    block_size = 5
    seen_blocks: Dict[str, List[Tuple[str, int]]] = {}

    for rel_path, content in file_map.items():
        lines = [line.strip() for line in content.splitlines()]
        # Skip very short files
        if len(lines) < block_size:
            continue
        for i in range(len(lines) - block_size + 1):
            chunk = "\n".join(lines[i:i + block_size])
            # Ignore empty or trivial blocks
            if len(chunk) < 60 or chunk.count("pass") > 2:
                continue
            if chunk in seen_blocks:
                seen_blocks[chunk].append((rel_path, i + 1))
            else:
                seen_blocks[chunk] = [(rel_path, i + 1)]

    reported_pairs = set()
    for chunk, occurrences in seen_blocks.items():
        if len(occurrences) > 1:
            first_file, first_line = occurrences[0]
            for other_file, other_line in occurrences[1:]:
                pair_key = tuple(sorted([f"{first_file}:{first_line}", f"{other_file}:{other_line}"]))
                if pair_key not in reported_pairs and first_file != other_file:
                    reported_pairs.add(pair_key)
                    findings.append({
                        "file": other_file,
                        "function": "duplicate_block",
                        "issue": "duplicate_code",
                        "detail": f"Duplicate logic block ({block_size} lines) identical to block in {first_file}:L{first_line}.",
                        "metric": f"{block_size} identical lines",
                        "severity": "medium",
                    })
    return findings


def parse_github_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parses a GitHub URL, handling root URLs, tree URLs, and subfolders.
    Returns (clone_url, branch, subpath).
    Example:
    'https://github.com/Vasu7389/react-project-ideas/tree/master/day001/counter-game/'
    -> ('https://github.com/Vasu7389/react-project-ideas.git', 'master', 'day001/counter-game')
    """
    clean = url.strip()
    m = re.match(
        r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/(?:tree|blob)/([^/]+)(?:/(.*))?)?/?$",
        clean,
        re.IGNORECASE,
    )
    if m:
        owner, repo, branch, subpath = m.groups()
        return f"https://github.com/{owner}/{repo}.git", branch, (subpath.strip("/") if subpath else None)
    return clean, None, None


def _safe_rmtree(path: str):
    """Safely removes directory on Windows, handling read-only git metadata."""
    import stat

    def on_error(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    shutil.rmtree(path, onerror=on_error, ignore_errors=True)


def clone_github_repo(repo_url: str) -> Tuple[str, str]:
    """
    Clones a public GitHub repo shallowly to a temporary directory.
    Returns (temp_dir_to_clean, scan_root_path).
    """
    clone_url, branch, subpath = parse_github_url(repo_url)
    temp_dir = tempfile.mkdtemp(prefix="codecourt_scan_")
    
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([clone_url, temp_dir])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    # If branch-specific clone fails, fallback to default branch
    if result.returncode != 0 and branch:
        cmd = ["git", "clone", "--depth", "1", clone_url, temp_dir]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        _safe_rmtree(temp_dir)
        err = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Git clone failed: {err}")

    scan_dir = temp_dir
    if subpath:
        sub_candidate = os.path.join(temp_dir, os.path.normpath(subpath))
        if os.path.exists(sub_candidate):
            scan_dir = sub_candidate
        else:
            for root, dirs, _ in os.walk(temp_dir):
                rel = os.path.relpath(root, temp_dir).replace("\\", "/")
                if rel.lower() == subpath.lower():
                    scan_dir = root
                    break

    return temp_dir, scan_dir


def scan_directory(target_path: str, is_github: bool = False) -> List[Dict[str, Any]]:
    """
    Main entry point for HEUSC.
    Scans a directory or git repo, parses AST, runs radon, computes metrics,
    and returns a normalized list of findings conforming to findings_schema.md.
    """
    cleanup_path = None
    scan_root = target_path

    if is_github or target_path.startswith("http://") or target_path.startswith("https://") or target_path.startswith("git@"):
        cleanup_path, scan_root = clone_github_repo(target_path)

    raw_findings: List[Dict[str, Any]] = []
    file_map: Dict[str, str] = {}
    py_files: List[Tuple[str, str]] = []
    js_files: List[Tuple[str, str]] = []

    try:
        # Collect source files
        for root, dirs, files in os.walk(scan_root):
            # Skip virtual environments, build artifacts, and hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "env", ".venv", "__pycache__", "node_modules", "dist", "build")]
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, scan_root).replace("\\", "/")
                if file.endswith(".py"):
                    py_files.append((full_p, rel_p))
                elif file.endswith((".js", ".jsx", ".ts", ".tsx")):
                    js_files.append((full_p, rel_p))

        # Check for missing tests
        all_source = [rp for _, rp in (py_files + js_files) if not rp.startswith("test") and "test" not in rp.lower() and "spec" not in rp.lower()]
        all_tests = [rp for _, rp in (py_files + js_files) if rp.startswith("test") or "test" in rp.lower() or "spec" in rp.lower()]
        if all_source and not all_tests:
            raw_findings.append({
                "file": "test_suite",
                "function": "global_suite",
                "issue": "missing_test_coverage",
                "detail": f"Repository contains {len(all_source)} source files but zero test files detected.",
                "metric": "0 test files",
                "severity": "high",
            })

        # Process Python files
        for full_p, rel_p in py_files:
            try:
                with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                file_map[rel_p] = content
                lines = content.splitlines()

                # Radon Complexity
                cc_issues = compute_radon_complexity(rel_p, content)
                for issue in cc_issues:
                    issue["file"] = rel_p
                    raw_findings.append(issue)

                # AST Audit
                try:
                    tree = ast.parse(content, filename=rel_p)
                    tag_parent_functions(tree)
                    auditor = ASTCodeAuditor(rel_p, rel_p, lines)
                    auditor.visit(tree)
                    for issue in auditor.issues:
                        issue["file"] = rel_p
                        raw_findings.append(issue)
                except SyntaxError as se:
                    raw_findings.append({
                        "file": rel_p,
                        "function": f"L{se.lineno}",
                        "issue": "syntax_error",
                        "detail": f"Failed to parse Python code: {se.msg}",
                        "metric": None,
                        "severity": "high",
                    })
            except Exception:
                continue

        # Process JavaScript / TypeScript / React files
        for full_p, rel_p in js_files:
            try:
                with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                file_map[rel_p] = content
                lines = content.splitlines()

                # Long file smell
                if len(lines) > 200:
                    raw_findings.append({
                        "file": rel_p,
                        "function": "file_scope",
                        "issue": "excessive_file_length",
                        "detail": f"File spans {len(lines)} lines (threshold is 200). Consider modularizing.",
                        "metric": f"{len(lines)} lines",
                        "severity": "medium",
                    })

                # Static patterns check
                for idx, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if "dangerouslySetInnerHTML" in stripped:
                        raw_findings.append({
                            "file": rel_p,
                            "function": f"L{idx}",
                            "issue": "xss_vulnerability_risk",
                            "detail": f"Direct use of dangerouslySetInnerHTML at L{idx} exposes application to XSS.",
                            "metric": f"L{idx}",
                            "severity": "high",
                        })
                    if re.search(r"\beval\(", stripped):
                        raw_findings.append({
                            "file": rel_p,
                            "function": f"L{idx}",
                            "issue": "dangerous_eval",
                            "detail": f"Use of eval() at L{idx} executes arbitrary code dynamically.",
                            "metric": f"L{idx}",
                            "severity": "high",
                        })
                    if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", stripped):
                        raw_findings.append({
                            "file": rel_p,
                            "function": f"L{idx}",
                            "issue": "swallowed_exception",
                            "detail": f"Empty catch block at L{idx} swallows runtime errors silently.",
                            "metric": f"L{idx}",
                            "severity": "medium",
                        })
            except Exception:
                continue

        # Code Duplication Check (cross-file)
        dups = detect_code_duplication(file_map)
        raw_findings.extend(dups)

    finally:
        if cleanup_path:
            _safe_rmtree(cleanup_path)

    # Format findings with unique IDs (F1, F2, ...)
    formatted_findings: List[Dict[str, Any]] = []
    for idx, f in enumerate(raw_findings, start=1):
        formatted_findings.append({
            "id": f"F{idx}",
            "file": f.get("file", "unknown"),
            "function": f.get("function", "module"),
            "issue": f.get("issue", "general_issue"),
            "detail": f.get("detail", ""),
            "metric": f.get("metric"),
            "severity": f.get("severity", "medium"),
        })

    return formatted_findings


def save_findings_to_json(findings: List[Dict[str, Any]], output_file: str = "findings.json") -> str:
    """Writes findings to a standardized JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
    return output_file
