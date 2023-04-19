#!/usr/bin/env python3

import lark
import sys
import enum
import collections

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

type           : int_t
               | bool_t
               | string_t
               | float_t
               | tuple_t
               | array_t
               | list_t

int_t          : "int"
bool_t         : "bool"
string_t       : "string"
float_t        : "float"
tuple_t        : "tuple" "<" type ("," type)+ ">"
array_t        : "array" "<" type "," int_literal ">"
list_t         : "list"  "<" type ">"

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
bool_literal   : /true|false/
float_literal  : /-?[0-9]+(\.[0-9]+)?/
list_literal   : "[" (expression ("," expression)*)? "]"
tuple_literal  : "(" expression ("," expression)+ ")"

%import common.WS
%ignore WS
'''


class Type(enum.Enum):
    INT = 0
    BOOL = 1
    FLOAT = 2
    STRING = 3


class IplInterpreter(lark.visitors.Interpreter):

    __vars__: collections.OrderedDict[str, Type]
    __num_of_vars_stack__: list[int]
    __num_of_new_vars__: int

    __keywords__: frozenset[str] = frozenset(
        [
            'fn', 'let', 'return', 'int', 'bool', 'string',
            'float', 'tuple', 'array', 'list', 'read', 'write',
            'if', 'else', 'elif', 'unless',
            'case', 'of', 'default'
            'while', 'for', 'do', 'in', 'head', 'tail'
            'true', 'false'
        ]
    )

    def __init__(self):
        self.__vars__ = collections.OrderedDict()
        self.__num_of_vars_stack__ = list()
        self.__num_of_new_vars__ = 0

    def __new_scope__(self):
        self.__num_of_vars_stack__.append(self.__num_of_new_vars__)
        self.__num_of_new_vars__ = 0

    def __end_scope__(self):
        for _ in range(0, self.__num_of_new_vars__):
            self.__vars__.popitem()
        self.__num_of_new_vars__ = self.__num_of_vars_stack__.pop()

    def unit(self, tree: lark.tree.Tree):
        for c in tree.children:
            self.visit(c)

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):

        self.__new_scope__()

        begin_index: int = 2
        if len(tree.children) > 2:
            begin_index += int(tree.children[2].data == 'type')

        for n in range(begin_index, len(tree.children)):
            self.visit(tree.children[n])

        self.__end_scope__()

    def func_params(self, tree: lark.tree.Tree):
        pass

    def var_defn(self, tree: lark.tree.Tree):
        self.__num_of_new_vars__ += 1
        self.visit(tree.children[0])

    def var_bind(self, tree: lark.tree.Tree):
        self.__vars__[tree.children[0].value] = self.visit(tree.children[1])

    def instruction(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def ret(self, tree: lark.tree.Tree):
        pass

    def attrib(self, tree: lark.tree.Tree):
        pass

    def type(self, tree: lark.tree.Tree):

        match tree.children[0].data:

            case 'int_t':
                return Type.INT

            case 'string_t':
                return Type.STRING

            case 'float_t':
                return Type.FLOAT

            case 'bool_t':
                return Type.BOOL

            case _:
                return None

    def int_t(self, tree: lark.tree.Tree):
        pass

    def bool_t(self, tree: lark.tree.Tree):
        pass

    def string_t(self, tree: lark.tree.Tree):
        pass

    def float_t(self, tree: lark.tree.Tree):
        pass

    def tuple_t(self, tree: lark.tree.Tree):
        pass

    def array_t(self, tree: lark.tree.Tree):
        pass

    def list_t(self, tree: lark.tree.Tree):
        pass

    def expression(self, tree: lark.tree.Tree):
        if isinstance(tree.children[0], lark.tree.Tree):
            self.visit(tree.children[0])
        elif not tree.children[0].value in self.__vars__:
            print(f"{tree.children[0].value}: variable not in scope")

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
        for c in tree.children:
            self.visit(c)

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
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        ind: int = 1
        for i in range(ind, len(tree.children)):
            if tree.children[i].data != 'instruction':
                ind = i
                break
            self.visit(tree.children[i])
        self.__end_scope__()

        for i in range(ind, len(tree.children)):
            self.visit(tree.children[i])

    def elif_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self.__end_scope__()

    def else_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for c in tree.children:
            self.visit(c)
        self.__end_scope__()

    def unless_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self.__end_scope__()

    def case_flow(self, tree: lark.tree.Tree):
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

    def of_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self.__end_scope__()

    def default_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for c in tree.children:
            self.visit(c)
        self.__end_scope__()

    def loop_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def while_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])
        self.__new_scope__()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self.__end_scope__()

    def do_while_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for n in range(1, len(tree.children) - 1):
            self.visit(tree.children[n])
        self.__end_scope__()

    def for_flow(self, tree: lark.tree.Tree):
        self.__new_scope__()
        for n in range(2, len(tree.children)):
            self.visit(tree.children[n])
        self.__end_scope__()

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
''',
        '''
let y: bool = true;

fn foo() {
    let x: float = 3.0;
    let b: bool = true;

    if(b){
        let a: string = "kddk";
    }
    elif(x == b){
        let sksj: string = "kdlls";
    }

    while(kk == uu){
        let h: float = 1.0;
    }
}

fn bar() {

}

'''
    ]

    parser: lark.Lark = lark.Lark(grammar, start='unit')

    for t in tests:

        try:
            tree: lark.ParseTree = parser.parse(t)
            interpreter: IplInterpreter = IplInterpreter()
            interpreter.transform(tree)

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
