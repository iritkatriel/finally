
import argparse
import ast
import glob
import os
import sys
import tarfile
import warnings


FINALLY = 'F'
LOOP = 'L'
DEF = 'D'

class Visitor(ast.NodeVisitor):
    def __init__(self, source, filename, findings):
        self.source = source
        self.filename = filename
        self.findings = findings
        self.state = []

    def do_Try(self, node):
        for n in node.body:
            self.visit(n)
        for n in node.handlers:
            self.visit(n)
        for n in node.orelse:
            self.visit(n)
        self.state.append(FINALLY)
        for n in node.finalbody:
            self.visit(n)
        self.state.pop()

    def do_Loop(self, node):
        self.state.append(LOOP)
        self.generic_visit(node)
        self.state.pop()

    def do_forbidden(self, node, good_state=None):
        assert good_state is not None
        if not self.state:
            return
        state = None
        for i in range(len(self.state), 0, -1):
            if self.state[i-1] in (FINALLY, good_state):
                state = self.state[i-1]
                break
        if state == FINALLY:
            self.findings.append([self.filename, self.source, node.lineno])
            print(self.filename, node.lineno)

    def do_FunctionDef(self, node):
        self.state.append(DEF)
        self.generic_visit(node)
        self.state.pop()

    def visit_FunctionDef(self, node):
        self.do_FunctionDef(node)

    def visit_Try(self, node):
        self.do_Try(node)

    def visit_TryStar(self, node):
        self.do_Try(node)

    def visit_For(self, node):
        self.do_Loop(node)

    def visit_While(self, node):
        self.do_Loop(node)

    def visit_Break(self, node):
        self.do_forbidden(node, good_state=LOOP)

    def visit_Continue(self, node):
        self.do_forbidden(node, good_state=LOOP)

    def visit_Return(self, node):
        self.do_forbidden(node, good_state=DEF)


class Reporter:

    def __init__(self):
        self.findings = []
        self.lines = 0

    def report(self, source, filename, verbose):
        try:
            a = ast.parse(source)
        except (SyntaxError, RecursionError) as e:
            # print(f'>>>   {type(e)} in ast.parse() for {filename}')
            return

        Visitor(source, filename, self.findings).visit(a)
        self.lines += len(source.split(b'\n'))

    def file_report(self, filename, verbose):
        try:
            with open(filename, "rb") as f:
                source = f.read()
            self.report(source, filename, verbose)
        except Exception as err:
            if verbose > 0:
                print(filename + ":", err)

    def tarball_report(self, filename, verbose):
        if verbose > 1:
            print(f"\nExamining tarball {filename}")
        with tarfile.open(filename, "r") as tar:
            members = tar.getmembers()
            for m in members:
                info = m.get_info()
                name = info["name"]
                if name.endswith(".py"):
                    try:
                        source = tar.extractfile(m).read()
                    except Exception as err:
                        if verbose > 0:
                            print(f"{name}: {err}")
                    else:
                        self.report(source, name, verbose-1)

def expand_globs(filenames):
    for filename in filenames:
        if "*" in filename and sys.platform == "win32":
            for fn in glob.glob(filename):
                yield fn
        else:
            yield filename

argparser = argparse.ArgumentParser()
argparser.add_argument("-q", "--quiet", action="store_true",
                       help="less verbose output")
argparser.add_argument("-v", "--verbose", action="store_true",
                       help="more verbose output")
argparser.add_argument("filenames", nargs="*", metavar="FILE",
                       help="files, directories or tarballs to count")


def main():
    args = argparser.parse_args()
    verbose = 1 + args.verbose - args.quiet
    filenames = args.filenames
    if not filenames:
        argparser.print_usage()
        sys.exit(0)

    if verbose < 2:
        warnings.filterwarnings("ignore", "", SyntaxWarning)

    if verbose >= 2:
        print("Looking for", ", ".join(OF_INTEREST_NAMES))
        print("In", filenames)

    reporter = Reporter()

    for filename in expand_globs(filenames):
        if os.path.isfile(filename):
            if filename.endswith(".tar.gz"):
                reporter.tarball_report(filename, verbose)
            else:
                reporter.file_report(filename, verbose)
        elif os.path.isdir(filename):
            for root, dirs, files in os.walk(filename):
                for file in files:
                    if file.endswith(".py"):
                        full = os.path.join(root, file)
                        reporter.file_report(full, verbose)
        else:
            print(f"{filename}: Cannot open")

    print(f'total lines: {reporter.lines}')

if __name__ == "__main__":
    main()
