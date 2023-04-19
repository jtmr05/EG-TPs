#!/usr/bin/env python3

import lark
import re
import sys
import enum
import collections

import utils


GRAMMAR: str = '''
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

type           : INT_T
               | BOOL_T
               | STRING_T
               | FLOAT_T
               | tuple_t
               | array_t
               | list_t

INT_T          : "int"
BOOL_T         : "bool"
STRING_T       : "string"
FLOAT_T        : "float"
tuple_t        : "tuple" "<" type ("," type)+ ">"
array_t        : "array" "<" type "," INT_LITERAL ">"
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
of_flow        : "of" "(" (INT_LITERAL|STRING_LITERAL) ")" "{" instruction* "}"
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

literal        : INT_LITERAL
               | STRING_LITERAL
               | BOOL_LITERAL
               | FLOAT_LITERAL
               | list_literal
               | tuple_literal
INT_LITERAL    : /-?[0-9]+/
STRING_LITERAL : /".*?"/
BOOL_LITERAL   : /true|false/
FLOAT_LITERAL  : /-?[0-9]+(\.[0-9]+)?/
list_literal   : "[" (expression ("," expression)*)? "]"
tuple_literal  : "(" expression ("," expression)+ ")"

%import common.WS
%ignore WS
'''

TERM_LITERAL_PATTERN: re.Pattern = re.compile('\b(INT|STRING|BOOL|FLOAT)_LITERAL\b')


class Type(enum.Enum):
    INT = 0
    BOOL = 1
    FLOAT = 2
    STRING = 3


class IplInterpreter(lark.visitors.Interpreter):

    _vars: collections.OrderedDict[str, Type]
    _num_of_vars_stack: list[int]
    _num_of_new_vars: int

    _keywords: frozenset[str] = frozenset(
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
        self._vars = collections.OrderedDict()
        self._num_of_vars_stack = list()
        self._num_of_new_vars = 0

    def _new_scope(self):
        self._num_of_vars_stack.append(self._num_of_new_vars)
        self._num_of_new_vars = 0

    def _end_scope(self):
        #print(self._vars)
        for _ in range(0, self._num_of_new_vars):
            self._vars.popitem()
        self._num_of_new_vars = self._num_of_vars_stack.pop()

    def unit(self, tree: lark.tree.Tree):
        for c in tree.children:
            self.visit(c)

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):

        self._new_scope()

        begin_index: int = 2
        if len(tree.children) > 2:
            begin_index += int(tree.children[2].data == 'type')

        for n in range(begin_index, len(tree.children)):
            self.visit(tree.children[n])

        self._end_scope()

    def func_params(self, tree: lark.tree.Tree):
        pass

    def var_defn(self, tree: lark.tree.Tree):
        self._num_of_new_vars += 1
        self.visit(tree.children[0])

    def var_bind(self, tree: lark.tree.Tree):
        self._vars[tree.children[0].value] = self.visit(tree.children[1])

    def instruction(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def ret(self, tree: lark.tree.Tree):
        pass

    def attrib(self, tree: lark.tree.Tree):
        pass

    def type(self, tree: lark.tree.Tree):

        if isinstance(tree.children[0], lark.lexer.Token):
            return Type[tree.children[0].value.upper()]

        return None

    def tuple_t(self, tree: lark.tree.Tree):
        pass

    def array_t(self, tree: lark.tree.Tree):
        pass

    def list_t(self, tree: lark.tree.Tree):
        pass

    def expression(self, tree: lark.tree.Tree):
        if isinstance(tree.children[0], lark.tree.Tree):
            self.visit(tree.children[0])
        elif not tree.children[0].value in self._vars:
            print(f"{tree.children[0].value}: variable not in scope")

    def plus_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        assert lhs_type == Type.FLOAT or lhs_type == Type.INT or lhs_type == Type.STRING
        return lhs_type

    def minus_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        assert lhs_type == Type.FLOAT or lhs_type == Type.INT
        return lhs_type

    def mul_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        assert lhs_type == Type.FLOAT or lhs_type == Type.INT
        return lhs_type

    def div_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        assert lhs_type == Type.FLOAT or lhs_type == Type.INT
        return lhs_type

    def mod_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == Type.INT
        assert rhs_type == Type.INT
        return Type.INT

    def exp_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        assert lhs_type == Type.FLOAT or lhs_type == Type.INT
        return lhs_type

    def prepend_expr(self, tree: lark.tree.Tree):
        # TODO return list type
        pass

    def append_expr(self, tree: lark.tree.Tree):
        # TODO return list type
        pass

    def eq_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        return Type.BOOL

    def neq_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        return Type.BOOL

    def and_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        return Type.BOOL

    def or_expr(self, tree: lark.tree.Tree):
        lhs_type: Type = self.visit(tree.children[0])
        rhs_type: Type = self.visit(tree.children[1])
        assert lhs_type == rhs_type
        return Type.BOOL

    def not_expr(self, tree: lark.tree.Tree):
        op_type: Type = self.visit(tree.children[0])
        assert op_type == Type.BOOL
        return Type.BOOL

    def func_call(self, tree: lark.tree.Tree):
        pass

    def control_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        ind: int = 1
        for i in range(ind, len(tree.children)):
            if tree.children[i].data != 'instruction':
                ind = i
                break
            self.visit(tree.children[i])
        self._end_scope()

        for i in range(ind, len(tree.children)):
            self.visit(tree.children[i])

    def elif_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self._end_scope()

    def else_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for c in tree.children:
            self.visit(c)
        self._end_scope()

    def unless_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self._end_scope()

    def case_flow(self, tree: lark.tree.Tree):
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

    def of_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self._end_scope()

    def default_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for c in tree.children:
            self.visit(c)
        self._end_scope()

    def loop_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def while_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])
        self._new_scope()
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])
        self._end_scope()

    def do_while_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for n in range(1, len(tree.children) - 1):
            self.visit(tree.children[n])
        self._end_scope()

    def for_flow(self, tree: lark.tree.Tree):
        self._new_scope()
        for n in range(2, len(tree.children)):
            self.visit(tree.children[n])
        self._end_scope()

    def read(self, tree: lark.tree.Tree):
        pass

    def write(self, tree: lark.tree.Tree):
        pass

    def head(self, tree: lark.tree.Tree):
        pass

    def tail(self, tree: lark.tree.Tree):
        pass

    def literal(self, tree: lark.tree.Tree):
        if match_obj := TERM_LITERAL_PATTERN.match(tree.children[0].data):
            return Type[match_obj.group(1)]
        return None

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

    parser: lark.Lark = lark.Lark(GRAMMAR, start='unit')

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
