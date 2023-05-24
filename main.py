#!/usr/bin/env python3

import lark
import sys
import os
import pydot

from grammar import GRAMMAR
from analyzer import StaticAnalysisInterpreter
from graphs import GraphInterpreter
from utils import annotate


def main() -> int:

    if len(sys.argv) == 1:
        print(f'usage: {sys.argv[0]} FILE...', file=sys.stderr)
        return 1

    out_dir: str = 'out/'
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    parser: lark.Lark = lark.Lark(GRAMMAR, start='unit')
    status: int = 0

    for ind, fn in enumerate(sys.argv[1:]):

        test: str = ''
        with open(fn, 'r') as in_fh:
            test = in_fh.read()

        with open('err.log', 'w') as log:
            try:
                tree: lark.ParseTree = parser.parse(test)
                static_analyzer: StaticAnalysisInterpreter = StaticAnalysisInterpreter()
                static_analyzer.transform(tree)

                html_fn: str = os.path.join(out_dir, f'output_test{ind + 1}.html')
                with open(html_fn, 'w') as html_fh:
                    html_fh.write(static_analyzer.get_html())

                if static_analyzer.has_errors():
                    print(
                        f"==> test '{annotate(test, 1)}'\n{annotate('passed', 32, 1)}...\n",
                        f"however, there were {annotate('errors', 1, 31)} detected!\n",
                        f"{annotate('skipping', 1, 36)} graph generation...\n",
                        file=sys.stderr,
                        sep=''
                    )
                    status = 2
                    continue

                print(
                    f"==> test '{annotate(test, 1)}'\n{annotate('passed', 32, 1)}!",
                    file=sys.stderr
                )
                graph_generator: GraphInterpreter = GraphInterpreter()
                graph_generator.transform(tree)

                pairs: list[tuple[str, pydot.Dot]] = graph_generator.get_func_name_graph_pairs()
                for func_name, graph in pairs:
                    dot_fn: str = os.path.join(out_dir, f'graph_test{ind + 1}_{func_name}.gv')
                    with open(dot_fn, 'w') as dot_fh:
                        dot_fh.write(graph.to_string())

                    graph.write_png(os.path.join(out_dir, f'graph_test{ind + 1}_{func_name}.png'))

            except (lark.UnexpectedCharacters, lark.GrammarError) as e:
                print(
                    f"==> test '{annotate(test, 1)}' {annotate('failed', 31, 1)}!",
                    file=sys.stderr
                )
                log.write(f'test {ind + 1} failed: {str(e)}')
                status = 3

            print("\n")

    return status


if __name__ == '__main__':
    sys.exit(main())
