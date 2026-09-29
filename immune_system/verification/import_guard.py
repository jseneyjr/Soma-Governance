"""Import Guard — Layer 1 tool for detecting unguarded third-party imports.

Scans Python files using AST to find import statements, classifies them
as stdlib or third-party, and checks whether third-party imports are
properly guarded (try/except or pytest.importorskip).

Catches the exact class of bug that broke CI: a bare `import yaml` in
a test file when PyYAML isn't in the project's dependency manifest.
"""
import ast
import os
import re
import sys
from dataclasses import dataclass

from . import ToolEvidence


# Build stdlib module set from the running interpreter
_STDLIB_MODULES: set[str] | None = None


def _get_stdlib_modules() -> set[str]:
    """Lazily compute the set of stdlib top-level module names."""
    global _STDLIB_MODULES
    if _STDLIB_MODULES is not None:
        return _STDLIB_MODULES

    # Python 3.10+ has sys.stdlib_module_names
    if hasattr(sys, 'stdlib_module_names'):
        _STDLIB_MODULES = set(sys.stdlib_module_names)
    else:
        # Fallback for older Python: use a hardcoded core set
        _STDLIB_MODULES = {
            'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat',
            'asyncio', 'asyncore', 'atexit', 'base64', 'bdb', 'binascii',
            'binhex', 'bisect', 'builtins', 'bz2', 'calendar', 'cgi',
            'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
            'codeop', 'collections', 'colorsys', 'compileall', 'concurrent',
            'configparser', 'contextlib', 'contextvars', 'copy', 'copyreg',
            'cProfile', 'crypt', 'csv', 'ctypes', 'curses', 'dataclasses',
            'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils',
            'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
            'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter',
            'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass',
            'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac',
            'html', 'http', 'idlelib', 'imaplib', 'imghdr', 'imp',
            'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json',
            'keyword', 'lib2to3', 'linecache', 'locale', 'logging',
            'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
            'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'nis',
            'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
            'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes',
            'pkgutil', 'platform', 'plistlib', 'poplib', 'posix',
            'posixpath', 'pprint', 'profile', 'pstats', 'pty', 'pwd',
            'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random',
            're', 'readline', 'reprlib', 'resource', 'rlcompleter',
            'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve',
            'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib',
            'sndhdr', 'socket', 'socketserver', 'spwd', 'sqlite3', 'sre_compile',
            'sre_constants', 'sre_parse', 'ssl', 'stat', 'statistics',
            'string', 'stringprep', 'struct', 'subprocess', 'sunau',
            'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny',
            'tarfile', 'telnetlib', 'tempfile', 'termios', 'test',
            'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token',
            'tokenize', 'tomllib', 'trace', 'traceback', 'tracemalloc',
            'tty', 'turtle', 'turtledemo', 'types', 'typing',
            'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv',
            'warnings', 'wave', 'weakref', 'webbrowser', 'winreg',
            'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc',
            'zipapp', 'zipfile', 'zipimport', 'zlib',
            # underscore-prefixed internals
            '_thread', '__future__',
        }
    return _STDLIB_MODULES


@dataclass
class ImportInfo:
    """A single import statement found in a source file."""
    module: str       # top-level module name (e.g. 'yaml', not 'yaml.safe_load')
    lineno: int       # line number in the source file
    guarded: bool     # True if inside try/except or via importorskip


def is_stdlib(module: str) -> bool:
    """Check if a module name is part of the Python standard library."""
    return module in _get_stdlib_modules()


# Pattern for pytest.importorskip("module_name")
_IMPORTORSKIP_RE = re.compile(
    r'''(?:pytest\.)?importorskip\(\s*['\"](\w+)['"]\s*\)'''
)


def extract_imports(filepath: str) -> list[ImportInfo]:
    """Extract all import statements from a Python source file.

    Detects:
    - `import foo` and `import foo.bar` (extracts top-level 'foo')
    - `from foo import bar` (extracts top-level 'foo')
    - `pytest.importorskip("foo")` (extracts 'foo', marked guarded)
    - try/except ImportError guards (marks enclosed imports as guarded)

    Args:
        filepath: Path to a .py file

    Returns:
        List of ImportInfo with module name, line number, and guard status
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    results: list[ImportInfo] = []

    # First pass: find importorskip calls via regex (not easily caught by AST)
    for match in _IMPORTORSKIP_RE.finditer(source):
        module = match.group(1)
        lineno = source[:match.start()].count('\n') + 1
        results.append(ImportInfo(module=module, lineno=lineno, guarded=True))

    # Second pass: AST-based import extraction
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return results

    # Collect line ranges of try blocks for guard detection
    try_ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            # Check if any handler catches ImportError or is bare except
            has_import_guard = False
            max_end = node.end_lineno or node.lineno
            for handler in node.handlers:
                if handler.end_lineno:
                    max_end = max(max_end, handler.end_lineno)
                if handler.type is None:
                    # bare except:
                    has_import_guard = True
                elif isinstance(handler.type, ast.Name) and handler.type.id in (
                    'ImportError', 'ModuleNotFoundError', 'Exception',
                ):
                    has_import_guard = True
            if has_import_guard:
                try_ranges.append((node.lineno, max_end))

    def _is_in_try(lineno: int) -> bool:
        return any(start <= lineno <= end for start, end in try_ranges)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                # Skip if already found via importorskip
                if any(r.module == module and r.guarded for r in results):
                    continue
                results.append(ImportInfo(
                    module=module,
                    lineno=node.lineno,
                    guarded=_is_in_try(node.lineno),
                ))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                if any(r.module == module and r.guarded for r in results):
                    continue
                results.append(ImportInfo(
                    module=module,
                    lineno=node.lineno,
                    guarded=_is_in_try(node.lineno),
                ))

    return results


def check(
    filepath: str,
    allowed_deps: set[str] | None = None,
    project_root: str | None = None,
) -> ToolEvidence:
    """Check a Python file for unguarded third-party imports.

    Args:
        filepath: Path to the Python source file
        allowed_deps: Set of allowed third-party module names
            (e.g. from pyproject.toml dependencies). Imports of these
            modules are not flagged even if unguarded.
        project_root: Root directory of the project. If provided,
            any top-level directory containing __init__.py is treated
            as a local package and not flagged.

    Returns:
        ToolEvidence with verdict=True if no unguarded third-party imports,
        False otherwise. Lines contains line numbers of violations.
    """
    if allowed_deps is None:
        allowed_deps = set()

    # Auto-detect local packages from project root
    # Handles both traditional packages (__init__.py) and namespace packages
    local_packages: set[str] = set()
    if project_root:
        for entry in os.listdir(project_root):
            if entry.startswith('.') or entry.startswith('_'):
                continue
            entry_path = os.path.join(project_root, entry)
            if os.path.isdir(entry_path):
                init_path = os.path.join(entry_path, '__init__.py')
                if os.path.exists(init_path):
                    local_packages.add(entry)
                else:
                    # Check for namespace package: contains .py files or sub-packages
                    try:
                        contents = os.listdir(entry_path)
                    except PermissionError:
                        continue
                    has_python = any(f.endswith('.py') for f in contents)
                    has_subpkg = any(
                        os.path.exists(os.path.join(entry_path, d, '__init__.py'))
                        for d in contents
                        if os.path.isdir(os.path.join(entry_path, d))
                    )
                    if has_python or has_subpkg:
                        local_packages.add(entry)

    imports = extract_imports(filepath)
    violations: list[tuple[str, int]] = []

    for imp in imports:
        if is_stdlib(imp.module):
            continue
        if imp.module in allowed_deps:
            continue
        if imp.module in local_packages:
            continue
        if imp.guarded:
            continue
        violations.append((imp.module, imp.lineno))

    if not violations:
        return ToolEvidence(
            tool="import_guard",
            target=os.path.basename(filepath),
            verdict=True,
            detail=f"All imports are stdlib, allowed, or guarded",
        )

    modules = [v[0] for v in violations]
    lines = sorted(v[1] for v in violations)
    return ToolEvidence(
        tool="import_guard",
        target=os.path.basename(filepath),
        verdict=False,
        detail=f"Unguarded third-party imports: {', '.join(modules)}",
        lines=lines,
    )

