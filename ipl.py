#!/usr/bin/env python3

import lark
import sys
import enum
import typing
import io
import textwrap

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
array_t        : "array" "<" type "," int_literal ">"
list_t         : "list"  "<" type ">"

expression     : prepend_expr
               | append_expr
               | or_expr
               | and_expr
               | eq_expr
               | neq_expr
               | plus_expr
               | minus_expr
               | mul_expr
               | div_expr
               | mod_expr
               | exp_expr
               | not_expr
               | func_call
               | read
               | head
               | tail
               | literal
               | var_deref
               | paren_expr
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
var_deref      : CONSTRUCT_ID "[" expression "]"
               | CONSTRUCT_ID
paren_expr     : "(" expression ")"
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
               | float_literal
               | BOOL_LITERAL
               | string_literal
               | list_literal
               | array_literal
               | tuple_literal
int_literal    : /-?[0-9]+/
float_literal  : /-?[0-9]+\.[0-9]+/
BOOL_LITERAL   : "true" | "false"
string_literal : STRING
list_literal   : "[" expression ("," expression)* "]"
array_literal  : "{" (expression ("," expression)*)? "}"
tuple_literal  : "(" (expression ("," expression)+)? ")"

%import common.WS
%import common.ESCAPED_STRING -> STRING
%ignore WS
'''

Typename = typing.Union['Type', tuple['Type', ...], tuple['Type', int]]  # à lá C++


class BaseType(enum.Enum):
    INT = 0
    BOOL = 1
    FLOAT = 2
    STRING = 3
    LIST = 4
    TUPLE = 5
    ARRAY = 6
    ANY = 7

    def __eq__(self, rhs: object):
        if rhs is None or not isinstance(rhs, BaseType):
            return False
        if self is rhs or self.value == BaseType.ANY or rhs.value == BaseType.ANY:
            return True
        return self.value == rhs.value


class Type:

    base: BaseType
    _typename: typing.Optional[Typename]

    def __init__(self, bt: BaseType, tn: Typename = None):
        self.base = bt
        self._typename = tn

    def __eq__(self, rhs: object) -> bool:
        if rhs is None or not isinstance(rhs, Type):
            return False
        if self is rhs or self.base == BaseType.ANY or rhs.base == BaseType.ANY:
            return True
        return self.base == rhs.base and self._typename == rhs._typename

    def is_param(self, t: 'Type') -> bool:
        return self._typename == t


class IplInterpreter(lark.visitors.Interpreter):

    _vars: dict[str, Type]
    _functions: set[str]
    _num_of_vars_stack: list[int]
    _num_of_new_vars: int
    _err_string: str
    _html_buffer: io.StringIO

    """_keywords: frozenset[str] = frozenset(
        [
            'fn', 'let', 'return', 'int', 'bool', 'string',
            'float', 'tuple', 'array', 'list', 'read', 'write',
            'if', 'else', 'elif', 'unless',
            'case', 'of', 'default'
            'while', 'for', 'do', 'in', 'head', 'tail'
            'true', 'false'
        ]
    )"""

    def __init__(self):
        self._vars = dict()
        self._functions = set()
        self._num_of_vars_stack = list()
        self._num_of_new_vars = 0
        self._err_string = None
        self._html_buffer = io.StringIO()
        self._html_buffer.write(
            textwrap.dedent(
                '''
                <!DOCTYPE html>
                <html>
                  <style>
                    .error {
                      position: relative;
                      display: inline-block;
                      border-bottom: 1px dotted black;
                      color: red;
                    }
                    .code {
                      position: relative;
                      display: inline-block;
                    }
                    .error .errortext {
                      visibility: hidden;
                      width: 500px;
                      background-color: #555;
                      color: #fff;
                      text-align: center;
                      border-radius: 6px;
                      padding: 5px 0;
                      position: absolute;
                      z-index: 1;
                      bottom: 125%;
                      left: 50%;
                      margin-left: -40px;
                      opacity: 0;
                      transition: opacity 0.3s;
                    }
                    .error .errortext::after {
                      content: "";
                      position: absolute;
                      top: 100%;
                      left: 20%;
                      margin-left: -5px;
                      border-width: 5px;
                      border-style: solid;
                      border-color: #555 transparent transparent transparent;
                    }
                    .error:hover .errortext {
                      visibility: visible;
                      opacity: 1;
                    }
                  </style>
                  <head>
                    <meta charset="utf-8" />
                    <title>Análise de Código</title>
                    <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css" />
                  </head>

                <body>
                  <h2>Análise de Código</h2>
                  <div class="w3-code"><pre>
                '''
            )
        )

    def _new_scope(self):
        self._num_of_vars_stack.append(self._num_of_new_vars)
        self._num_of_new_vars = 0

    def _end_scope(self):
        for _ in range(0, self._num_of_new_vars):
            self._vars.popitem()
        self._num_of_new_vars = self._num_of_vars_stack.pop()

    def _set_err_string(self, s: str):
        if self._err_string is None:
            self._err_string = s

    def _flush_err_string(self, code: str):
        if self._err_string is not None:
            self._html_buffer.write(f'<div class="error">{code}')
            self._html_buffer.write(f'<span class="errortext">{self._err_string}</span></div>\n')
        else:
            self._html_buffer.write(f'{code}\n')
        self._err_string = None

    def _add_var(self, var_id: str, var_type: Type):
        if var_id not in self._vars:
            self._vars[var_id] = var_type
            self._num_of_new_vars += 1
        else:
            self._set_err_string('Variable already defined')

    def get_html(self) -> str:
        return self._html_buffer.getvalue()

    def unit(self, tree: lark.tree.Tree):
        for c in tree.children:
            self.visit(c)
        self._html_buffer.write('</pre></div></body></html>')

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):
        if tree.children[0] not in self._functions:
            self._functions.add(tree.children[0])
        else:
            self._set_err_string('Function already defined')

        self._new_scope()

        params_code: str = self.visit(tree.children[1])
        type_code: str = ''
        if tree.children[2].data == 'type':
            _, code = self.visit(tree.children[2])
            type_code = f" -> {code} "

        self._flush_err_string(f'fn {tree.children[0]}{params_code}{type_code}{{')

        for c in tree.find_data('instruction'):
            self.visit(c)

        self._html_buffer.write('}\n')
        self._end_scope()

    def func_params(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()
        for c in tree.children:
            var_id, var_type, bind_code = self.visit(c)
            self._add_var(var_id, var_type)
            code_strs.append(bind_code)
        code_str: str = f"({', '.join([str(x) for x in code_strs])})"
        return code_str

    def var_defn(self, tree: lark.tree.Tree):
        var_id, var_type, bind_code = self.visit(tree.children[0])
        self._add_var(var_id, var_type)

        expr_tn, expr_code = self.visit(tree.children[1])
        if expr_tn != var_type:
            self._set_err_string('Mismatched types')

        self._flush_err_string(f"let {bind_code} = {expr_code};")

    def var_bind(self, tree: lark.tree.Tree) -> tuple[str, Type, str]:
        tn, code = self.visit(tree.children[1])
        return tree.children[0], tn, f"{tree.children[0]}: {code}"

    def instruction(self, tree: lark.tree.Tree):
        ret = self.visit(tree.children[0])
        if ret is not None:
            self._flush_err_string(f"{ret[1]};")

    def ret(self, tree: lark.tree.Tree):
        tn, code = self.visit(tree.children[0])
        self._flush_err_string(f'return {code};')

    def attrib(self, tree: lark.tree.Tree):
        var: str = tree.children[0]
        value_tn, value_code = self.visit(tree.children[-1])

        if len(tree.children) == 2:
            if var not in self._vars:
                self._set_err_string('Variable not in scope')
            elif value_tn != self._vars.get(var):
                self._set_err_string('Mismatched types in assignment')
            self._flush_err_string(f'{var} = {value_code};')
        else:
            ind_tn, ind_code = self.visit(tree.children[1])
            if var not in self._vars:
                self._set_err_string('Variable not in scope')
            elif self._vars.get(var).base != BaseType.ARRAY:
                self._set_err_string('Type of lhs operand for operator [] must be array')
            elif value_tn != self._vars.get(var)._typename:
                self._set_err_string('Mismatched types in assignment')
            elif ind_tn.base != BaseType.INT:
                self._set_err_string('Type of rhs operand for operator [] must be int')
            self._flush_err_string(f'{var}[{ind_code}] = {value_code};')

    def type(self, tree: lark.tree.Tree) -> (Type, str):
        if isinstance(tree.children[0], lark.lexer.Token):  # primitive type
            return Type(BaseType[tree.children[0].upper()]), tree.children[0]
        else:
            return self.visit(tree.children[0])

    def tuple_t(self, tree: lark.tree.Tree) -> (Type, str):
        typenames: list[Type] = list()
        code_strs: list[str] = list()
        for c in tree.children:
            tn, code = self.visit(c)
            typenames.append(tn)
            code_strs.append(code)

        code_str: str = f"tuple&lt;{str(code_strs)[1:-1]}&gt;"
        return Type(BaseType.TUPLE, tuple(typenames)), code_str

    def array_t(self, tree: lark.tree.Tree) -> (Type, str):
        tn, code = self.visit(tree.children[0])
        _, size = self.visit(tree.children[1])
        return Type(BaseType.ARRAY, (tn, int(size))), f"array&lt;{code}, {size}&gt;"

    def list_t(self, tree: lark.tree.Tree) -> (Type, str):
        tn, code = self.visit(tree.children[0])
        return Type(BaseType.LIST, tn), f"list&lt;{code}&gt;"

    def expression(self, tree: lark.tree.Tree) -> (Type, str):
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])

    def plus_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator + must be the same')
        elif tn_lhs.base != BaseType.FLOAT and tn_lhs.base != BaseType.INT:
            self._set_err_string('Type of operands for operator + must be int, float or string')
        return tn_lhs, f"{code_lhs} + {code_rhs}"

    def minus_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator - must be the same')
        elif tn_lhs.base != BaseType.FLOAT and tn_lhs.base != BaseType.INT:
            self._set_err_string('Type of operands for operator - must be int or float')
        return tn_lhs, f"{code_lhs} - {code_rhs}"

    def mul_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator * must be the same')
        elif tn_lhs.base != BaseType.FLOAT and tn_lhs.base != BaseType.INT:
            self._set_err_string('Type of operands for operator * must be int or float')
        return tn_lhs, f"{code_lhs} * {code_rhs}"

    def div_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator / must be the same')
        elif tn_lhs.base != BaseType.FLOAT and tn_lhs.base != BaseType.INT:
            self._set_err_string('Type of operands for operator / must be int or float')
        return tn_lhs, f"{code_lhs} / {code_rhs}"

    def mod_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs.base != BaseType.INT or tn_rhs.base != BaseType.INT:
            self._set_err_string('Type of operands for operator % must be int')
        return Type(BaseType.INT), f"{code_lhs} % {code_rhs}"

    def exp_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator ^ must be the same')
        elif tn_lhs.base != BaseType.FLOAT and tn_lhs.base != BaseType.INT:
            self._set_err_string('Type of operands for operator ^ must be int or float')
        return tn_lhs, f"{code_lhs} ^ {code_rhs}"

    def prepend_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_rhs.base != BaseType.LIST:
            self._set_err_string('Type of rhs operand for operator ^: must be list')
        elif not tn_rhs.is_param(tn_lhs):
            self._set_err_string(
                'Type of lhs operand for operator ^: must be the same as rhs\'s typename'
            )
        return tn_rhs, f"{code_lhs} ^: {code_rhs}"

    def append_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_rhs.base != BaseType.LIST:
            self._set_err_string('Type of rhs operand for operator $: must be list')
        elif not tn_rhs.is_param(tn_lhs):
            self._set_err_string(
                'Type of lhs operand for operator $: must be the same as rhs\'s typename'
            )
        return tn_rhs, f"{code_lhs} $: {code_rhs}"

    def eq_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator == must be the same')
        return Type(BaseType.BOOL), f"{code_lhs} == {code_rhs}"

    def neq_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator != must be the same')
        return Type(BaseType.BOOL), f"{code_lhs} != {code_rhs}"

    def and_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs.base != BaseType.BOOL or tn_rhs.base != BaseType.BOOL:
            self._set_err_string('Type of operands for operator &amp;&amp; must be bool')
        return Type(BaseType.BOOL), f"{code_lhs} &amp;&amp; {code_rhs}"

    def or_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs.base != BaseType.BOOL or tn_rhs.base != BaseType.BOOL:
            self._set_err_string('Type of operands for operator || must be bool')
        return Type(BaseType.BOOL), f"{code_lhs} || {code_rhs}"

    def not_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.BOOL:
            self._set_err_string('Type of operand for operator ! must be bool')
        return Type(BaseType.BOOL), f"!{code}"

    def paren_expr(self, tree: lark.tree.Tree) -> (Type, str):
        tn, code = self.visit(tree.children[0])
        return tn, f"({code})"

    def var_deref(self, tree: lark.tree.Tree) -> (Type, str):

        if len(tree.children) == 2:
            tn, code = self.visit(tree.children[1])

            if tree.children[0] not in self._vars:
                self._set_err_string('Variable not in scope')
                return Type(BaseType.ANY), f"{tree.children[0]}[{code}]"
            elif self._vars.get(tree.children[0]).base != BaseType.ARRAY:
                self._set_err_string('Type of lhs operand for operator [] must be array')
            elif tn.base != BaseType.INT:
                self._set_err_string('Type of rhs operand for operator [] must be int')
            return self._vars.get(tree.children[0]), f"{tree.children[0]}[{code}]"
        else:
            if tree.children[0] not in self._vars:
                self._set_err_string('Variable not in scope')
                return Type(BaseType.ANY), tree.children[0]
            else:
                return self._vars.get(tree.children[0]), tree.children[0]

    def func_call(self, tree: lark.tree.Tree) -> str:
        if tree.children[0] not in self._functions:
            self._set_err_string('Function not in scope')

        code_strs: list[str] = list()
        for c in tree.find_data('expression'):
            tn, code = self.visit(c)
            code_strs.append(code)

        return Type(BaseType.ANY), f"{tree.children[0]}({', '.join([str(x) for x in code_strs])})"

    def control_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'if({code}){{')

        for c in tree.find_data('instruction'):
            self.visit(c)

        self._html_buffer.write('}\n')
        self._end_scope()

        for c in tree.find_data('elif_flow'):
            self.visit(c)
        for c in tree.find_data('else_flow'):
            self.visit(c)

    def elif_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'elif({code}){{')

        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

        self._html_buffer.write('}\n')
        self._end_scope()

    def else_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        self._html_buffer.write('else {\n')
        for c in tree.children:
            self.visit(c)

        self._html_buffer.write('}\n')
        self._end_scope()

    def unless_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'unless({code}){{')

        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

        self._html_buffer.write('}\n')
        self._end_scope()

    def case_flow(self, tree: lark.tree.Tree):

        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.INT and tn.base != BaseType.STRING:
            self._set_err_string('Type of case expression must be int or string')

        self._flush_err_string(f'case({code}){{\n')
        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

        self._html_buffer.write('}\n')

    def of_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        _, code = self.visit(tree.children[0])
        self._html_buffer.write(f'of({code}){{\n')

        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

        self._html_buffer.write('}\n')
        self._end_scope()

    def default_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        self._html_buffer.write('default {\n')

        for c in tree.children:
            self.visit(c)

        self._html_buffer.write('}\n')
        self._end_scope()

    def loop_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def while_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'while({code}){{')

        for n in range(1, len(tree.children)):
            self.visit(tree.children[n])

        self._html_buffer.write('}\n')
        self._end_scope()

    def do_while_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        self._html_buffer.write('do {')

        for n in range(0, len(tree.children) - 1):
            self.visit(tree.children[n])

        tn, code = self.visit(tree.children[-1])
        if tn.base != BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'}} while({code});\n')
        self._end_scope()

    def for_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        tn, code = self.visit(tree.children[1])
        self._add_var(tree.children[0], tn)
        if tn.base != BaseType.LIST and tn.base != BaseType.ARRAY:
            self._set_err_string('Type of expression must iterable')

        self._flush_err_string(f'for({tree.children[0]} in {code}){{')

        for n in range(2, len(tree.children)):
            self.visit(tree.children[n])

        self._html_buffer.write('}\n')
        self._end_scope()

    def read(self, tree: lark.tree.Tree) -> (Type, str):
        return Type(BaseType.ANY), 'read()'

    def write(self, tree: lark.tree.Tree):
        code_strs: list[str] = list()
        for c in tree.children:
            _, code = self.visit(c)
            code_strs.append(code)
        self._flush_err_string(f"write({str(code_strs)[1:-1]});")

    def head(self, tree: lark.tree.Tree) -> (Type, str):
        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.LIST:
            self._set_err_string('head() operations can be only be used on lists')
        return tn._typename, f"head({code})"

    def tail(self, tree: lark.tree.Tree) -> (Type, str):
        tn, code = self.visit(tree.children[0])
        if tn.base != BaseType.LIST:
            self._set_err_string('list() operations can be only be used on lists')
        return tn, f"tail({code})"

    def literal(self, tree: lark.tree.Tree) -> (Type, str):
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])
        else:
            return Type(BaseType.BOOL), tree.children[0]

    def int_literal(self, tree: lark.tree.Tree) -> (Type, int):
        return Type(BaseType.INT), int(tree.children[0])

    def string_literal(self, tree: lark.tree.Tree) -> (Type, str):
        return Type(BaseType.STRING), tree.children[0]

    def float_literal(self, tree: lark.tree.Tree) -> (Type, float):
        return Type(BaseType.FLOAT), float(tree.children[0])

    def list_literal(self, tree: lark.tree.Tree) -> (Type, str):
        if len(tree.children) == 0:
            return Type(BaseType.ANY), '[]'

        tn0, code0 = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for i in range(1, len(tree.children)):
            tn, code = self.visit(tree.children[i])
            code_strs.append(code)
            if tn0 != tn:
                self._set_err_string('Lists must have homogeneous types')

        code_str: str = f"[{', '.join([str(x) for x in code_strs])}]"
        return Type(BaseType.LIST, tn0), code_str

    def array_literal(self, tree: lark.tree.Tree) -> (Type, str):
        if len(tree.children) == 0:
            return Type(BaseType.ANY), r'{}'

        tn0, code0 = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for i in range(1, len(tree.children)):
            tn, code = self.visit(tree.children[i])
            code_strs.append(code)
            if tn0 != tn:
                self._set_err_string('Arrays must have homogeneous types')

        code_str: str = f"{{{', '.join([str(x) for x in code_strs])}}}"
        return Type(BaseType.ARRAY, (tn0, len(tree.children))), code_str

    def tuple_literal(self, tree: lark.tree.Tree) -> (Type, str):
        typenames: list[Type] = list()
        code_strs: list[str] = list()
        for c in tree.children:
            tn, code = self.visit(c)
            typenames.append(tn)
            code_strs.append(code)

        code_str: str = f"({str(code_strs)[1:-1]})"
        return Type(BaseType.TUPLE, tuple(typenames)), code_str


def main() -> int:

    tests: list[str] = [
        '''
let y: bool = true;

fn foo(var: int, baz: string) -> bool {
    let x: float = 3.0;
    return 3 $: [1];
    bar();
    unless(x == 4.0){
        return false;
    }

    if(true != false){
        if(true){
        }
    }
    elif(1 + 1){ }
    else { }
    x = 4.5;
}

fn bar() {
    let i: array<int, 4> = {};
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
#        '''
#let y: bool = true;
#
#fn foo() {
#    let x: float = 3.0;
#    let b: bool = true;
#
#    if(x){
#        let a: string = "kddk";
#    }
#    elif(x == b){
#        let sksj: string = "kdlls";
#    }
#
#    while(kk == uu){
#        let h: float = 1.0;
#    }
#}
#
#fn bar() {
#
#}
#'''
    ]

    parser: lark.Lark = lark.Lark(GRAMMAR, start='unit')

    for t in tests:

        try:
            tree: lark.ParseTree = parser.parse(t)
            interpreter: IplInterpreter = IplInterpreter()
            interpreter.transform(tree)

            print(tree.pretty())
            with open('output.html', 'w') as fh:
                fh.write(interpreter.get_html())

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

        #print("\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
