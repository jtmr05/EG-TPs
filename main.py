#!/usr/bin/env python3

import lark
import sys
import os
import io
import pydot
import re

from grammar import GRAMMAR
from analyzer import StaticAnalysisInterpreter
from graphs import GraphInterpreter
from utils import annotate


def _slurp_file(fn: str) -> str:
    with open(fn, 'r') as fh:
        return fh.read()


def _dump_to_file(fn: str, content: str):
    with open(fn, 'w') as fh:
        fh.write(content)


def _gen_outputs(
    base_fn: str,
    test: str,
    log: io.TextIOWrapper,
    parser: lark.Lark,
    out_dir: str
) -> int:

    status: int = 0

    try:
        tree: lark.ParseTree = parser.parse(test)
        static_analyzer: StaticAnalysisInterpreter = StaticAnalysisInterpreter()
        static_analyzer.transform(tree)

        html_str: str = static_analyzer.get_html()
        html_fn: str = os.path.join(out_dir, f'output_{base_fn}.html')

        if static_analyzer.has_errors():
            print(
                f"==> test '{annotate(test, 1)}'\n{annotate('passed', 32, 1)}...\n",
                f"however, there were {annotate('errors', 1, 31)} detected!\n",
                f"{annotate('skipping', 1, 36)} graph generation...\n",
                file=sys.stderr,
                sep=''
            )
            status = 2

        else:
            print(
                f"==> test '{annotate(test, 1)}'\n{annotate('passed', 32, 1)}!",
                file=sys.stderr
            )
            graph_generator: GraphInterpreter = GraphInterpreter()
            graph_generator.transform(tree)

            pairs: list[tuple[str, pydot.Dot]] = graph_generator.get_func_name_graph_pairs()
            for func_name, graph in pairs:
                graph_base_fn: str = f'graph_{base_fn}_{func_name}'
                graph_full_fn: str = os.path.join(out_dir, graph_base_fn)
                _dump_to_file(f"{graph_full_fn}.gv", graph.to_string())
                graph.write_png(f"{graph_full_fn}.png")

                html_str = re.sub(
                    f'^fn {func_name}',
                    f'fn <a href="{graph_base_fn}.png">{func_name}</a>',
                    html_str,
                    flags=re.MULTILINE
                )

        _dump_to_file(html_fn, html_str)

    except (lark.UnexpectedCharacters, lark.GrammarError) as e:
        print(
            f"==> test '{annotate(test, 1)}' {annotate('failed', 31, 1)}!",
            file=sys.stderr
        )
        log.write(f'test {base_fn} failed: {str(e)}')
        status = 3

    return status


def main() -> int:

    if len(sys.argv) == 1:
        print(f'usage: {sys.argv[0]} FILE...', file=sys.stderr)
        return 1

    out_dir: str = 'out/'
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    parser: lark.Lark = lark.Lark(GRAMMAR, start='unit')
    status: int = 0

    for fn in sys.argv[1:]:

        base_fn: str = os.path.splitext(os.path.split(fn)[1])[0]
        test: str = _slurp_file(fn)
        with open('err.log', 'w') as log:
            if (curr_status := _gen_outputs(base_fn, test, log, parser, out_dir)) != 0:
                status = curr_status

        print("\n")

    return status


if __name__ == '__main__':
    sys.exit(main())
