#!/usr/bin/env python3
"""Local-variable budget check (BD-539).

Luau refuses to compile a function that needs more than 200 local registers
("Out of local registers ... exceeded limit 200"). The main chunk of a script is a
function too, so a huge UI file such as src/client/Bootstrap.client.luau can break the
whole client by gaining one more top-level `local`.

For every .luau under src/ this counts the locals that are live at the same time in each
function scope (the main chunk included) using the Luau AST from `luau-ast`:

  * function arguments (and `self` for methods) count,
  * `local`, `local function` count when they are declared and stop counting when their
    block ends (locals in sibling blocks are NOT added together),
  * a local that is initialised with a literal (number, string, true/false/nil, -number)
    and never reassigned is a compile-time constant: Luau gives it no register, so it is
    not counted either (measured: 300 such locals compile fine),
  * loop variables count (one for a numeric `for`, one per name in `for ... in`); the
    hidden loop-state registers are not locals and do not count toward the 200 limit,
  * nested functions are their own scope and are reported separately.

The count is the live-locals peak, the registers the compiler needs for named variables.
Temporaries during an expression are extra, which is why the fail line (185) sits below
the compiler limit (200). Measured on Bootstrap.client.luau: this count was 196 and the
compiler accepted exactly 4 more non-constant locals.

  python tools/verify_local_budget.py --ast PATH/luau-ast        # check src/
  python tools/verify_local_budget.py --top 10                   # also print the top scopes
  python tools/verify_local_budget.py --selftest --compiler PATH/luau-compile

Exit 1 when any scope exceeds FAIL_ABOVE (185). Warnings above WARN_ABOVE (140). All of src/ (server, client, shared) is scanned.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WARN_ABOVE = 140  # docs/150: WeatherVisuals.client grew 110 -> 147 and Bootstrap sat at 198 inside one day; warn early, fail at 185
FAIL_ABOVE = 185
COMPILER_LIMIT = 200
# A ratchet for scopes that were once close to the limit: (file under the repo, scope name) -> highest live-locals count allowed. Lower it
# when code moves out, never raise it (BD-1088: the Bootstrap main chunk went 142 -> 128 when the shop screens moved to ShopScreens.luau, then 122 with the toast stack in Toasts.luau, then 118 when the Dino Index and details moved to DinoIndexScreens.luau, then 116 with the small screens in SmallScreens.luau).
SCOPE_CEILINGS = {("src/client/Bootstrap.client.luau", "<main chunk>"): 118}


def find_tool(explicit, sibling_of, name, env):
    """Locate a luau tool: explicit path, next to another tool, env var, then PATH."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    if sibling_of:
        base = Path(sibling_of).parent
        candidates += [base / name, base / (name + ".exe")]
    if os.environ.get(env):
        candidates.append(os.environ[env])
    found = shutil.which(name)
    if found:
        candidates.append(found)
    for candidate in candidates:
        resolved = shutil.which(str(candidate)) or (str(candidate) if Path(candidate).is_file() else None)
        if resolved:
            return resolved
    return None


def parse_ast(ast_tool, path):
    done = subprocess.run([ast_tool, str(path)], capture_output=True, check=False)
    if done.returncode != 0:
        raise RuntimeError("luau-ast failed on %s: %s" % (path, done.stderr.decode("utf-8", "replace").strip()))
    return json.loads(done.stdout.decode("utf-8"))["root"]


LITERALS = ("AstExprConstantNumber", "AstExprConstantString", "AstExprConstantBool", "AstExprConstantNil")


def is_literal(node):
    kind = node.get("type")
    if kind in LITERALS:
        return True
    return kind == "AstExprUnary" and node.get("op") == "Minus" and node["expr"].get("type") == "AstExprConstantNumber"


def location_key(var):
    return (var.get("name"), var.get("location"))


def collect_assigned(node, out):
    """Declaration keys of every local that is the target of an assignment anywhere in the file."""
    if isinstance(node, list):
        for item in node:
            collect_assigned(item, out)
    elif isinstance(node, dict):
        kind = node.get("type")
        targets = []
        if kind == "AstStatAssign":
            targets = node.get("vars", [])
        elif kind == "AstStatCompoundAssign":
            targets = [node.get("var")]
        for target in targets:
            if target and target.get("type") == "AstExprLocal":
                out.add(location_key(target["local"]))
        for key, value in node.items():
            if isinstance(value, (dict, list)) and key not in ("location", "luauType"):
                collect_assigned(value, out)


def line_of(node):
    loc = node.get("location", "0,0 - 0,0")
    return int(loc.split(",", 1)[0]) + 1


class Scopes:
    """Collects (name, line, peak) for the chunk and every function in one file."""

    def __init__(self, assigned=frozenset()):
        self.found = []
        self.assigned = assigned

    def counted(self, stmt):
        """Registers a `local` statement really takes (literal never-assigned locals take none)."""
        variables = stmt.get("vars", [])
        values = stmt.get("values", [])
        if len(variables) != len(values):
            return len(variables)
        return sum(
            0 if (is_literal(value) and location_key(var) not in self.assigned) else 1
            for var, value in zip(variables, values)
        )

    def block(self, node, base):
        """Peak live locals inside an AstStatBlock whose enclosing scope already holds base."""
        cur = base
        peak = base
        for stmt in node.get("body", []):
            kind = stmt.get("type")
            if kind == "AstStatLocal":
                self.visit(stmt.get("values", []), cur)
                cur += self.counted(stmt)
            elif kind == "AstStatLocalFunction":
                cur += 1
                self.visit(stmt.get("func"), cur)
            else:
                peak = max(peak, self.stmt(stmt, cur))
            peak = max(peak, cur)
        return peak

    def stmt(self, node, cur):
        kind = node.get("type")
        if kind == "AstStatFor":
            self.visit([node.get("from"), node.get("to"), node.get("step")], cur)
            return self.block(node["body"], cur + 1)
        if kind == "AstStatForIn":
            self.visit(node.get("values", []), cur)
            return self.block(node["body"], cur + len(node.get("vars", [])))
        if kind == "AstStatRepeat":
            # the condition sees the body locals; it declares none of its own
            peak = self.block(node["body"], cur)
            self.visit(node.get("condition"), cur)
            return peak
        return self.visit(node, cur)

    def visit(self, node, cur):
        """Walk any node; blocks use block(), functions open a new scope. Returns the peak."""
        peak = cur
        if isinstance(node, list):
            for item in node:
                peak = max(peak, self.visit(item, cur))
        elif isinstance(node, dict):
            kind = node.get("type")
            if kind == "AstExprFunction":
                self.function(node)
            elif kind == "AstStatBlock":
                peak = max(peak, self.block(node, cur))
            elif kind in ("AstStatFor", "AstStatForIn", "AstStatRepeat"):
                peak = max(peak, self.stmt(node, cur))
            else:
                for key, value in node.items():
                    if isinstance(value, (dict, list)) and key not in ("location", "luauType"):
                        peak = max(peak, self.visit(value, cur))
        return peak

    def function(self, node):
        args = len(node.get("args", [])) + (1 if node.get("self") else 0)
        peak = self.block(node["body"], args)
        name = node.get("debugname") or "<anonymous>"
        self.found.append((name, line_of(node), max(peak, args)))


def scopes_of_source(ast_tool, path):
    root = parse_ast(ast_tool, path)
    assigned = set()
    collect_assigned(root, assigned)
    scopes = Scopes(assigned)
    peak = scopes.block(root, 0)
    scopes.found.append(("<main chunk>", 1, peak))
    return scopes.found


def scan(ast_tool, src_root):
    rows = []
    for path in sorted(src_root.rglob("*.luau")):
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
        for name, line, count in scopes_of_source(ast_tool, path):
            rows.append((count, rel, name, line))
    rows.sort(key=lambda row: (-row[0], row[1], row[3]))
    return rows


def describe(row):
    count, rel, name, line = row
    return "%3d locals  %s:%d  %s" % (count, rel, line, name)


def compiler_rejects(compiler, path):
    done = subprocess.run([compiler, str(path)], capture_output=True, check=False)
    text = (done.stdout + done.stderr).decode("utf-8", "replace")
    return done.returncode != 0, text


def selftest(ast_tool, compiler):
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        def make(name, body):
            path = tmp / name
            path.write_text(body, encoding="utf-8")
            return path

        def counts(path):
            return {name: count for name, _, count in scopes_of_source(ast_tool, path)}

        many = lambda n: "".join("local a%d = math.random()\n" % i for i in range(n)) + "print(a0)\n"
        over = make("over.luau", many(201))
        edge = make("edge.luau", many(200))
        if counts(over)["<main chunk>"] != 201:
            failures.append("201-local file counted as %s" % counts(over)["<main chunk>"])
        if counts(over)["<main chunk>"] <= FAIL_ABOVE:
            failures.append("201-local file would not be flagged")
        if counts(edge)["<main chunk>"] != 200:
            failures.append("200-local file counted as %s" % counts(edge)["<main chunk>"])
        if compiler:
            rejected, text = compiler_rejects(compiler, over)
            if not rejected or "local registers" not in text:
                failures.append("luau-compile did not reject the 201-local file: %s" % text.strip())
            rejected, text = compiler_rejects(compiler, edge)
            if rejected:
                failures.append("luau-compile rejected the 200-local file: %s" % text.strip())
            print("selftest: luau-compile on 201 locals -> %s" % compiler_rejects(compiler, over)[1].strip().splitlines()[0])
        print("selftest: verifier on 201 locals -> %d (fail above %d)" % (counts(over)["<main chunk>"], FAIL_ABOVE))

        # scoping rules: sibling blocks and nested functions do not add up
        shape_lines = [
            "local top = X",
            "do local a, b = X, X end",
            "do local c, d, e = X, X, X end",
            "local function f(x, y)",
            "  local z = X",
            "  return function(q) local w1, w2, w3 = X, X, X return w1 end",
            "end",
            "for i = 1, 2 do local k = i end",
            "for key, value in pairs({}) do local m = key end",
            "local obj = {}",
            "function obj:method(p) local r = X end",
            "repeat local rep = X until rep > 0",
        ]
        shape = make("shape.luau", "\n".join(shape_lines).replace("X", "os.clock()") + "\n")
        got = counts(shape)
        # main chunk peak: top, f + the for-in key, value, m = 5 (sibling do-blocks are not summed)
        expected = {"<main chunk>": 5, "f": 3, "method": 3}
        for name, want in expected.items():
            if got.get(name) != want:
                failures.append("shape test %s: wanted %s got %s" % (name, want, got.get(name)))
        consts_src = "".join("local k%d = %d\n" % (n, n) for n in range(300))
        consts_src += "local n = -1\nlocal m = 5\nm = 6\nlocal s = os.clock()\n"
        consts = make("consts.luau", consts_src)
        if counts(consts)["<main chunk>"] != 2:
            failures.append("constant locals counted as %s, wanted 2 (reassigned m + call s)" % counts(consts)["<main chunk>"])
        if compiler and compiler_rejects(compiler, consts)[0]:
            failures.append("luau-compile rejected 300 literal constants")
        anonymous = [count for name, _, count in scopes_of_source(ast_tool, shape) if name == "<anonymous>"]
        if anonymous != [4]:
            failures.append("anonymous function count wanted [4] got %s" % anonymous)
    for failure in failures:
        print("selftest FAIL: " + failure, file=sys.stderr)
    if not failures:
        print("selftest ok")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ast", help="path to luau-ast (default: next to --compiler, $LUAU_AST, or PATH)")
    parser.add_argument("--compiler", help="path to luau-compile (selftest cross-check; also locates luau-ast)")
    parser.add_argument("--src", default=str(ROOT / "src"), help="folder to scan (default src/)")
    parser.add_argument("--top", type=int, default=0, help="print the top N scopes by count")
    parser.add_argument("--selftest", action="store_true", help="prove the verifier on synthetic files and exit")
    args = parser.parse_args()

    ast_tool = find_tool(args.ast, args.compiler, "luau-ast", "LUAU_AST")
    if not ast_tool:
        print("verify_local_budget: luau-ast not found (pass --ast or --compiler next to it)", file=sys.stderr)
        return 2
    compiler = find_tool(args.compiler, args.ast, "luau-compile", "LUAU_COMPILE") if (args.compiler or args.selftest) else None
    if args.selftest:
        return selftest(ast_tool, compiler)

    rows = scan(ast_tool, Path(args.src))
    bad = [row for row in rows if row[0] > FAIL_ABOVE]
    over_ceiling = [row for row in rows if row[0] > SCOPE_CEILINGS.get((row[1], row[2]), 1000) and row not in bad]
    warn = [row for row in rows if WARN_ABOVE < row[0] <= FAIL_ABOVE]
    if args.top:
        print("top %d scopes by live locals (compiler limit %d):" % (args.top, COMPILER_LIMIT))
        for row in rows[: args.top]:
            print("  " + describe(row))
    for row in warn:
        print("WARN (above %d, fails above %d): %s" % (WARN_ABOVE, FAIL_ABOVE, describe(row)))
    for row in bad:
        print("FAIL (above %d, compiler limit %d): %s" % (FAIL_ABOVE, COMPILER_LIMIT, describe(row)), file=sys.stderr)
    for row in over_ceiling:
        print("FAIL (ratchet %d for this scope, see SCOPE_CEILINGS): %s" % (SCOPE_CEILINGS[(row[1], row[2])], describe(row)), file=sys.stderr)
    if over_ceiling:
        return 1
    if bad:
        print("Group related locals into a table or move a block into a module before adding more.", file=sys.stderr)
        return 1
    print("local budget ok: %d scopes in %s, highest %d" % (len(rows), args.src and Path(args.src).name, rows[0][0] if rows else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
