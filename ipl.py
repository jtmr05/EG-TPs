#!/usr/bin/env python3

import lark
import sys

import utils


grammar: str = '''
unit           : construct*
construct      : func_defn
               | var_defn

func_defn      : "fn" CONSTRUCT_ID func_params ("->" type)? "{" instruction* "}"
func_params    : "(" (var_bind ("," var_bind)*)? ")"

var_defn       : "let" var_bind "=" expression ";"

var_bind       : CONSTRUCT_ID ":" type

instruction    : var_defn
               | ret
               | control_flow
               | attrib
               | write
               | func_call ";"

ret            : "return" expression ";"

attrib         : CONSTRUCT_ID "=" expression ";"
               | CONSTRUCT_ID "[" expression "]" "=" expression ";"

type           : "int"
               | "bool"
               | "string"
               | "float"
               | "tuple" "<" type ("," type)+ ">"
               | "array" "<" type "," int_literal ">"
               | "list"  "<" type ">"

expression     : "(" expression ")"
               | plus_expr
               | minus_expr
               | mul_expr
               | div_expr
               | mod_expr
               | exp_expr
               | prepend_expr
               | append_expr
               | eq_expr
               | neq_expr
               | and_expr
               | or_expr
               | not_expr
               | CONSTRUCT_ID "[" expression "]"
               | CONSTRUCT_ID
               | literal
               | func_call
               | read
               | head
               | tail
plus_expr      : expression "+" expression
minus_expr     : expression "-" expression
mul_expr       : expression "*" expression
div_expr       : expression "/" expression
mod_expr       : expression "%" expression
exp_expr       : expression "^" expression
prepend_expr   : expression "^:" expression
append_expr    : expression "$:" expression
eq_expr        : expression "==" expression
neq_expr       : expression "!=" expression
and_expr       : expression "&&" expression
or_expr        : expression "||" expression
not_expr       : "!" expression

func_call      : CONSTRUCT_ID "(" (expression ("," expression)*)? ")"


control_flow   : branch_flow
               | loop_flow

branch_flow    : if_flow
               | unless_flow
               | case_flow
if_flow        : "if" "(" expression ")" "{" instruction* "}" elif_flow* else_flow?
elif_flow      : "elif" "(" expression ")" "{" instruction* "}"
else_flow      : "else" "{" instruction* "}"
unless_flow    : "unless" "(" expression ")" "{" instruction* "}"
case_flow      : "case" "(" expression ")" "{" of_flow* default_flow "}"
of_flow        : "of" "(" (int_literal|string_literal) ")" "{" instruction* "}"
default_flow   : "default" "{" instruction* "}"


loop_flow      : while_flow
               | do_while_flow
               | for_flow
while_flow     : "while" "(" expression ")" "{" instruction* "}"
do_while_flow  : "do" "{" instruction* "}" "while" "(" expression ")" ";"
for_flow       : "for" "(" CONSTRUCT_ID "in" expression ")" "{" instruction* "}"


read           : "read" "(" ")"
write          : "write" "(" expression ("," expression)* ")" ";"

head           : "head" "(" expression ")"
tail           : "tail" "(" expression ")"

CONSTRUCT_ID   : /[_A-Za-z][_A-Za-z0-9]*/

literal        : int_literal
               | string_literal
               | bool_literal
               | float_literal
               | list_literal
               | tuple_literal
int_literal    : /-?[0-9]+/
string_literal : /".*?"/
bool_literal   : "true" | "false"
float_literal  : /-?[0-9]+(\.[0-9]+)?/
list_literal   : "[" (expression ("," expression)*)? "]"
tuple_literal  : "(" expression ("," expression)+ ")"

%import common.WS
%ignore WS
'''


class ImperativeProgrammingLanguageInterpreter(lark.visitors.Interpreter):

    def unit(self, tree: lark.tree.Tree):
        pass

    def construct(self, tree: lark.tree.Tree):
        pass

    def func_defn(self, tree: lark.tree.Tree):
        pass

    def func_params(self, tree: lark.tree.Tree):
        pass

    def var_defn(self, tree: lark.tree.Tree):
        pass

    def var_bind(self, tree: lark.tree.Tree):
        pass

    def instruction(self, tree: lark.tree.Tree):
        pass

    def ret(self, tree: lark.tree.Tree):
        pass

    def attrib(self, tree: lark.tree.Tree):
        pass

    def type(self, tree: lark.tree.Tree):
        pass

    def expression(self, tree: lark.tree.Tree):
        pass

    def plus_expr(self, tree: lark.tree.Tree):
        pass

    def minus_expr(self, tree: lark.tree.Tree):
        pass

    def mul_expr(self, tree: lark.tree.Tree):
        pass

    def div_expr(self, tree: lark.tree.Tree):
        pass

    def mod_expr(self, tree: lark.tree.Tree):
        pass

    def exp_expr(self, tree: lark.tree.Tree):
        pass

    def prepend_expr(self, tree: lark.tree.Tree):
        pass

    def append_expr(self, tree: lark.tree.Tree):
        pass

    def eq_expr(self, tree: lark.tree.Tree):
        pass

    def neq_expr(self, tree: lark.tree.Tree):
        pass

    def and_expr(self, tree: lark.tree.Tree):
        pass

    def or_expr(self, tree: lark.tree.Tree):
        pass

    def not_expr(self, tree: lark.tree.Tree):
        pass

    def func_call(self, tree: lark.tree.Tree):
        pass

    def control_flow(self, tree: lark.tree.Tree):
        pass

    def branch_flow(self, tree: lark.tree.Tree):
        pass

    def if_flow(self, tree: lark.tree.Tree):
        pass

    def elif_flow(self, tree: lark.tree.Tree):
        pass

    def else_flow(self, tree: lark.tree.Tree):
        pass

    def unless_flow(self, tree: lark.tree.Tree):
        pass

    def case_flow(self, tree: lark.tree.Tree):
        pass

    def of_flow(self, tree: lark.tree.Tree):
        pass

    def default_flow(self, tree: lark.tree.Tree):
        pass

    def loop_flow(self, tree: lark.tree.Tree):
        pass

    def while_flow(self, tree: lark.tree.Tree):
        pass

    def do_while_flow(self, tree: lark.tree.Tree):
        pass

    def for_flow(self, tree: lark.tree.Tree):
        pass

    def read(self, tree: lark.tree.Tree):
        pass

    def write(self, tree: lark.tree.Tree):
        pass

    def head(self, tree: lark.tree.Tree):
        pass

    def tail(self, tree: lark.tree.Tree):
        pass

    def literal(self, tree: lark.tree.Tree):
        pass

    def int_literal(self, tree: lark.tree.Tree):
        pass

    def string_literal(self, tree: lark.tree.Tree):
        pass

    def bool_literal(self, tree: lark.tree.Tree):
        pass

    def float_literal(self, tree: lark.tree.Tree):
        pass

    def list_literal(self, tree: lark.tree.Tree):
        pass

    def tuple_literal(self, tree: lark.tree.Tree):
        pass


def main() -> int:

    tests: list[str] = [
        '''
let y: bool = true;

fn foo(var: int, baz: string) -> array<list<tuple<int, string>>, 10> {
    let x: float = 3.0;
    return 3 $: [];
    bar();
    unless(x == 4){
        return false;
    }

    if(true != false){
        if(true){
        }
    }
    elif(1 + 1){ }
    else { }
    x = 3;
}

fn bar() {
    let i: array<int, 4> = [1,2,3,45];
    case(1+1){
        of(1){ }
        of(2){ }
        default { }
    }

    while(true){ }

    for(a in [1,2,3]){ read(); }

    return (1+1, 2+2);
}
'''
    ]

    parser: lark.Lark = lark.Lark(grammar, start='unit')

    for t in tests:

        try:
            parser.parse(t)
            print(
                f"==> test '{utils.annotate(t, 1)}' {utils.annotate('passed', 32, 1)}!",
                file=sys.stderr
            )

        except lark.UnexpectedCharacters:
            print(
                f"==> test '{utils.annotate(t, 1)}' {utils.annotate('failed', 31, 1)}!",
                file=sys.stderr
            )

        except lark.GrammarError:
            print(
                f"==> test '{utils.annotate(t, 1)}' {utils.annotate('failed', 31, 1)}!",
                file=sys.stderr
            )

        print("\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
