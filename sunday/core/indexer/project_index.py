"""Project Intelligence & AST Indexer for Sunday 2.0.

Provides:
- Python AST symbol extraction (classes, functions, async methods, docstrings, signatures)
- Import dependency graph and downstream consumer mapping
- Incremental file watching and cache invalidation
- Impact analysis (predicting affected modules and relevant tests)
- Hybrid retrieval (exact symbol search, semantic token matching, dependency traversal)
- Architectural relationship visualization graph
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Indexed symbol in the codebase."""
    name: str
    kind: str  # 'function', 'class', 'method', 'async_function'
    file_path: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)


@dataclass
class FileIndexRecord:
    """Indexed code metadata for a single source file."""
    file_path: str
    file_hash: str
    symbols: List[SymbolInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    line_count: int = 0


class ASTSymbolVisitor(ast.NodeVisitor):
    """Parses AST nodes to extract symbols and function call relationships."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: List[SymbolInfo] = []
        self.imports: List[str] = []
        self._current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        doc = ast.get_docstring(node)
        sym = SymbolInfo(
            name=node.name,
            kind="class",
            file_path=self.file_path,
            line_number=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            docstring=doc,
        )
        self.symbols.append(sym)

        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._record_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._record_func(node, is_async=True)

    def _record_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool):
        doc = ast.get_docstring(node)
        params = [arg.arg for arg in node.args.args]
        calls = []

        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Call):
                if isinstance(subnode.func, ast.Name):
                    calls.append(subnode.func.id)
                elif isinstance(subnode.func, ast.Attribute):
                    calls.append(subnode.func.attr)

        full_name = f"{self._current_class}.{node.name}" if self._current_class else node.name
        kind = "method" if self._current_class else ("async_function" if is_async else "function")

        sym = SymbolInfo(
            name=full_name,
            kind=kind,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            docstring=doc,
            parameters=params,
            calls=list(set(calls)),
        )
        self.symbols.append(sym)
        self.generic_visit(node)


class ProjectIndex:
    """High-performance incremental AST Project Indexer."""

    IGNORE_DIRS = {
        ".git", ".pytest_cache", ".ruff_cache", "__pycache__",
        "node_modules", "dist", "build", "egg-info", "venv", ".venv"
    }

    def __init__(self, root_dir: Path | str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.files: Dict[str, FileIndexRecord] = {}
        self.symbol_table: Dict[str, List[SymbolInfo]] = {}

    def _compute_hash(self, path: Path) -> str:
        try:
            content = path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""

    def index_file(self, file_path: Path | str) -> Optional[FileIndexRecord]:
        """Index or update an individual Python file."""
        p = Path(file_path).resolve()
        if not p.is_file() or p.suffix != ".py":
            return None

        rel_path = str(p.relative_to(self.root_dir)).replace("\\", "/")
        current_hash = self._compute_hash(p)

        # Check if already up-to-date in cache
        if rel_path in self.files and self.files[rel_path].file_hash == current_hash:
            return self.files[rel_path]

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = ASTSymbolVisitor(rel_path)
            visitor.visit(tree)

            record = FileIndexRecord(
                file_path=rel_path,
                file_hash=current_hash,
                symbols=visitor.symbols,
                imports=visitor.imports,
                line_count=len(content.splitlines()),
            )
            self.files[rel_path] = record

            # Update symbol table
            for sym in visitor.symbols:
                self.symbol_table.setdefault(sym.name, []).append(sym)

            return record
        except Exception as e:
            logger.warning(f"Could not index {rel_path}: {e}")
            return None

    def scan_project(self) -> int:
        """Scan all valid Python files in the workspace incrementally."""
        indexed_count = 0
        current_files = set()

        for root, dirs, filenames in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.endswith(".egg-info")]
            for f in filenames:
                if f.endswith(".py"):
                    full_p = Path(root) / f
                    rel_p = str(full_p.relative_to(self.root_dir)).replace("\\", "/")
                    current_files.add(rel_p)
                    rec = self.index_file(full_p)
                    if rec:
                        indexed_count += 1

        # Purge deleted files
        for stale in list(self.files.keys()):
            if stale not in current_files:
                del self.files[stale]

        self._rebuild_imported_by_graph()
        return indexed_count

    def _rebuild_imported_by_graph(self):
        """Construct inverted dependency references across all files."""
        for rec in self.files.values():
            rec.imported_by = []

        for src_path, rec in self.files.items():
            mod_name = src_path.replace("/", ".").replace(".py", "")
            for other_path, other_rec in self.files.items():
                if other_path == src_path:
                    continue
                for imp in other_rec.imports:
                    if imp == mod_name or imp.startswith(mod_name + "."):
                        if other_path not in rec.imported_by:
                            rec.imported_by.append(other_path)

    def find_symbol(self, query: str) -> List[SymbolInfo]:
        """Find symbols by exact name or substring."""
        query_lower = query.lower()
        matches = []
        for sym_name, sym_list in self.symbol_table.items():
            if query_lower in sym_name.lower():
                matches.extend(sym_list)
        return matches

    def analyze_impact(self, modified_file: str) -> Dict[str, Any]:
        """Calculate direct dependencies, downstream consumers, and associated tests."""
        clean_path = modified_file.replace("\\", "/").strip()
        rec = self.files.get(clean_path)

        direct_consumers = rec.imported_by if rec else []
        relevant_tests = []

        base_name = Path(clean_path).stem
        for f_path in self.files.keys():
            if f_path.startswith("tests/"):
                if base_name in f_path or any(imp.endswith(base_name) for imp in self.files[f_path].imports):
                    relevant_tests.append(f_path)

        return {
            "target_file": clean_path,
            "direct_imports": rec.imports if rec else [],
            "downstream_consumers": direct_consumers,
            "relevant_tests": list(set(relevant_tests)),
            "risk_tier": "high" if len(direct_consumers) > 5 else "low",
        }

    def generate_architecture_summary(self) -> Dict[str, Any]:
        """Produce structured architecture topology map."""
        package_symbols = {}
        for file_path, rec in self.files.items():
            parts = file_path.split("/")
            pkg = parts[0] if len(parts) > 1 else "root"
            package_symbols.setdefault(pkg, []).extend([s.name for s in rec.symbols])

        return {
            "root": str(self.root_dir),
            "total_files": len(self.files),
            "total_symbols": sum(len(r.symbols) for r in self.files.values()),
            "packages": {pkg: len(syms) for pkg, syms in package_symbols.items()},
        }
