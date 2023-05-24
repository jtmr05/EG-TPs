import lark
import enum
import typing
import io
import textwrap
import inspect


_Typename = typing.Union['_Type', tuple['_Type', ...], tuple['_Type', int]]  # à lá C++


class _BaseType(enum.Enum):
    INT = 0
    BOOL = 1
    FLOAT = 2
    STRING = 3
    LIST = 4
    TUPLE = 5
    ARRAY = 6
    VOID = 7
    ANY = 8

    def __eq__(self, rhs: object):
        print(type(rhs))
        print(inspect.stack()[1][3], '\n')
        if rhs is None or not isinstance(rhs, _BaseType):
            return False
        if self is rhs or self.value == _BaseType.ANY.value or rhs.value == _BaseType.ANY.value:
            return True
        return self.value == rhs.value


class _Type:

    base: _BaseType
    typename: typing.Optional[_Typename]

    def __init__(self, bt: _BaseType, tn: _Typename = None):
        self.base = bt
        self.typename = tn

    def __eq__(self, rhs: object) -> bool:
        if rhs is None or not isinstance(rhs, _Type):
            return False
        if self is rhs or self.base == _BaseType['ANY'] or rhs.base == _BaseType['ANY']:
            return True
        return self.base == rhs.base and self.typename == rhs.typename

    def is_param(self, t: '_Type') -> bool:
        return self.typename == t


class StaticAnalysisInterpreter(lark.visitors.Interpreter):

    _vars: dict[str, _Type]
    _fns_params: dict[str, tuple[_Type, ...]]
    _fns_ret_types: dict[str, _Type]
    _curr_fn: typing.Optional[str]
    _num_of_vars_stack: list[int]
    _num_of_new_vars: int
    _err_string: typing.Optional[str]
    _has_errors: bool
    _indent_str: str
    _html_buffer: io.StringIO

    def __init__(self):
        self._vars = dict()
        self._fns_params = dict()
        self._fns_ret_types = dict()
        self._curr_fn = None
        self._num_of_vars_stack = list()
        self._num_of_new_vars = 0
        self._err_string = None
        self._has_errors = False
        self._indent_str = ''
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
                      width: 700px;
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
        self._indent()

    def _end_scope(self):
        for _ in range(0, self._num_of_new_vars):
            self._vars.popitem()
        self._num_of_new_vars = self._num_of_vars_stack.pop()
        self._dedent()

    def _set_err_string(self, s: str):
        if self._err_string is None:
            self._err_string = s
            self._has_errors = True

    def _flush_err_string(self, code: str):
        if self._err_string is not None:
            self._html_buffer.write(f'<div class="error">{code}')
            self._html_buffer.write(f'<span class="errortext">{self._err_string}</span></div>\n')
        else:
            self._html_buffer.write(f'{code}\n')
        self._err_string = None

    def _add_var(self, var_id: str, var_type: _Type):
        if var_id not in self._vars:
            self._vars[var_id] = var_type
            self._num_of_new_vars += 1
        else:
            self._set_err_string('Variable already defined')

    def _indent(self):
        self._indent_str += (' ' * 4)

    def _dedent(self):
        self._indent_str = self._indent_str[:-4]

    def get_html(self) -> str:
        self._html_buffer.write('</pre></div></body></html>')
        return self._html_buffer.getvalue()

    def has_errors(self) -> bool:
        return self._has_errors

    #def unit(self, tree: lark.tree.Tree):
    #    for c in tree.children:
    #        self.visit(c)
    #    self._html_buffer.write('</pre></div></body></html>')

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):
        self._new_scope()

        param_types, params_code = self.visit(tree.children[1])

        if tree.children[0] not in self._fns_params:
            self._fns_params[tree.children[0]] = param_types
            self._curr_fn = tree.children[0]
        else:
            self._set_err_string('Function already defined')
            self._curr_fn = None

        type_code: str = ''
        inst_ind: int = 2
        if len(tree.children) > 2 and tree.children[2].data == 'type':
            inst_ind += 1
            ret_type, code = self.visit(tree.children[2])
            type_code: str = f" -&gt; {code} "
            if self._curr_fn is not None:
                self._fns_ret_types[tree.children[0]] = ret_type
        elif self._curr_fn is not None:
            self._fns_ret_types[tree.children[0]] = _Type(_BaseType.VOID)

        self._flush_err_string(f'fn {tree.children[0]}{params_code}{type_code}{{')

        for c in tree.children[inst_ind:]:
            self.visit(c)

        self._curr_fn = None
        self._html_buffer.write('}\n\n')
        self._end_scope()

    def func_params(self, tree: lark.tree.Tree) -> tuple[tuple[_Type, ...], str]:
        code_strs: list[str] = list()
        param_types: list[_Type] = list()

        for c in tree.children:
            var_id, var_type, bind_code = self.visit(c)
            self._add_var(var_id, var_type)
            param_types.append(var_type)
            code_strs.append(bind_code)

        return tuple(param_types), f"({', '.join(code_strs)})"

    def var_defn(self, tree: lark.tree.Tree):
        var_id, var_type, bind_code = self.visit(tree.children[0])
        self._add_var(var_id, var_type)

        expr_tn, expr_code = self.visit(tree.children[1])
        if expr_tn != var_type:
            self._set_err_string('Mismatched types')

        self._flush_err_string(f"{self._indent_str}let {bind_code} = {expr_code};")

    def var_bind(self, tree: lark.tree.Tree) -> tuple[str, _Type, str]:
        tn, code = self.visit(tree.children[1])
        return tree.children[0], tn, f"{tree.children[0]}: {code}"

    def instruction(self, tree: lark.tree.Tree):
        if ret := self.visit(tree.children[0]):
            self._flush_err_string(f"{self._indent_str}{ret[1]};")

    def ret(self, tree: lark.tree.Tree):
        if len(tree.children) == 1:
            tn, code = self.visit(tree.children[0])
            if self._curr_fn is not None and tn != self._fns_ret_types.get(self._curr_fn):
                self._set_err_string('Mismatched types in return statement')

            self._flush_err_string(f'{self._indent_str}return {code};')
        else:
            if (
                self._curr_fn is not None
                and _BaseType.VOID != self._fns_ret_types.get(self._curr_fn).base
            ):
                self._set_err_string('Mismatched types in return statement')

            self._flush_err_string(f'{self._indent_str}return;')

    def attrib(self, tree: lark.tree.Tree):
        var: str = tree.children[0]
        expr_tn, expr_code = self.visit(tree.children[-1])

        if len(tree.children) == 2:
            if var not in self._vars:
                self._set_err_string('Variable not in scope')
            elif expr_tn != self._vars.get(var):
                self._set_err_string('Mismatched types in assignment')
            self._flush_err_string(f'{self._indent_str}{var} = {expr_code};')
        else:
            ind_tn, ind_code = self.visit(tree.children[1])
            if var not in self._vars:
                self._set_err_string('Variable not in scope')
            elif self._vars.get(var).base != _BaseType.ARRAY:
                self._set_err_string('Type of lhs operand for operator [] must be array')
            elif expr_tn != self._vars.get(var).typename[0]:
                self._set_err_string('Mismatched types in assignment')
            elif ind_tn.base != _BaseType.INT:
                self._set_err_string('Type of rhs operand for operator [] must be int')
            self._flush_err_string(f'{self._indent_str}{var}[{ind_code}] = {expr_code};')

    def type(self, tree: lark.tree.Tree) -> (_Type, str):
        if isinstance(tree.children[0], lark.lexer.Token):  # primitive type
            return _Type(_BaseType[tree.children[0].upper()]), tree.children[0]
        else:
            return self.visit(tree.children[0])

    def tuple_t(self, tree: lark.tree.Tree) -> (_Type, str):
        typenames: list[_Type] = list()
        code_strs: list[str] = list()
        for c in tree.children:
            tn, code = self.visit(c)
            typenames.append(tn)
            code_strs.append(code)

        return (
            _Type(_BaseType.TUPLE, tuple(typenames)),
            f"tuple&lt;{', '.join(code_strs)}&gt;"
        )

    def array_t(self, tree: lark.tree.Tree) -> (_Type, str):
        tn, code = self.visit(tree.children[0])
        _, size = self.visit(tree.children[1])
        return _Type(_BaseType.ARRAY, (tn, int(size))), f"array&lt;{code}, {size}&gt;"

    def list_t(self, tree: lark.tree.Tree) -> (_Type, str):
        tn, code = self.visit(tree.children[0])
        return _Type(_BaseType.LIST, tn), f"list&lt;{code}&gt;"

    def expression(self, tree: lark.tree.Tree) -> (_Type, str):
        return self.visit(tree.children[0])

    def plus_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator + must be the same')
        elif (
            tn_lhs.base != _BaseType.FLOAT
            and tn_lhs.base != _BaseType.INT
            and tn_lhs.base != _BaseType.STRING
        ):
            self._set_err_string('Type of operands for operator + must be int, float or string')
        return tn_lhs, f"{code_lhs} + {code_rhs}"

    def minus_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator - must be the same')
        elif tn_lhs.base != _BaseType.FLOAT and tn_lhs.base != _BaseType.INT:
            self._set_err_string('Type of operands for operator - must be int or float')
        return tn_lhs, f"{code_lhs} - {code_rhs}"

    def mul_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator * must be the same')
        elif tn_lhs.base != _BaseType.FLOAT and tn_lhs.base != _BaseType.INT:
            self._set_err_string('Type of operands for operator * must be int or float')
        return tn_lhs, f"{code_lhs} * {code_rhs}"

    def div_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator / must be the same')
        elif tn_lhs.base != _BaseType.FLOAT and tn_lhs.base != _BaseType.INT:
            self._set_err_string('Type of operands for operator / must be int or float')
        return tn_lhs, f"{code_lhs} / {code_rhs}"

    def mod_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs.base != _BaseType.INT or tn_rhs.base != _BaseType.INT:
            self._set_err_string('Type of operands for operator % must be int')
        return _Type(_BaseType.INT), f"{code_lhs} % {code_rhs}"

    def exp_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator ^ must be the same')
        elif tn_lhs.base != _BaseType.FLOAT and tn_lhs.base != _BaseType.INT:
            self._set_err_string('Type of operands for operator ^ must be int or float')
        return tn_lhs, f"{code_lhs} ^ {code_rhs}"

    def prepend_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_rhs.base != _BaseType.LIST:
            self._set_err_string('Type of rhs operand for operator ^: must be list')
        elif not tn_rhs.is_param(tn_lhs):
            self._set_err_string(
                'Type of lhs operand for operator ^: must be the same as rhs\'s typename'
            )
        return tn_rhs, f"{code_lhs} ^: {code_rhs}"

    def append_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_rhs.base != _BaseType.LIST:
            self._set_err_string('Type of rhs operand for operator $: must be list')
        elif not tn_rhs.is_param(tn_lhs):
            self._set_err_string(
                'Type of lhs operand for operator $: must be the same as rhs\'s typename'
            )
        return tn_rhs, f"{code_lhs} $: {code_rhs}"

    def eq_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator == must be the same')
        return _Type(_BaseType.BOOL), f"{code_lhs} == {code_rhs}"

    def neq_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs != tn_rhs:
            self._set_err_string('Type of operands for operator != must be the same')
        return _Type(_BaseType.BOOL), f"{code_lhs} != {code_rhs}"

    def and_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs.base != _BaseType.BOOL or tn_rhs.base != _BaseType.BOOL:
            self._set_err_string('Type of operands for operator &amp;&amp; must be bool')
        return _Type(_BaseType.BOOL), f"{code_lhs} &amp;&amp; {code_rhs}"

    def or_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn_lhs, code_lhs = self.visit(tree.children[0])
        tn_rhs, code_rhs = self.visit(tree.children[1])
        if tn_lhs.base != _BaseType.BOOL or tn_rhs.base != _BaseType.BOOL:
            self._set_err_string('Type of operands for operator || must be bool')
        return _Type(_BaseType.BOOL), f"{code_lhs} || {code_rhs}"

    def not_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.BOOL:
            self._set_err_string('Type of operand for operator ! must be bool')
        return _Type(_BaseType.BOOL), f"!{code}"

    def paren_expr(self, tree: lark.tree.Tree) -> (_Type, str):
        tn, code = self.visit(tree.children[0])
        return tn, f"({code})"

    def var_deref(self, tree: lark.tree.Tree) -> (_Type, str):

        if len(tree.children) == 2:
            tn, code = self.visit(tree.children[1])

            if tree.children[0] not in self._vars:
                self._set_err_string('Variable not in scope')
                return _Type(_BaseType.ANY), f"{tree.children[0]}[{code}]"
            elif self._vars.get(tree.children[0]).base != _BaseType.ARRAY:
                self._set_err_string('Type of lhs operand for operator [] must be array')
            elif tn.base != _BaseType.INT:
                self._set_err_string('Type of rhs operand for operator [] must be int')
            return self._vars.get(tree.children[0]), f"{tree.children[0]}[{code}]"
        else:
            if tree.children[0] not in self._vars:
                self._set_err_string('Variable not in scope')
                return _Type(_BaseType.ANY), tree.children[0]
            else:
                return self._vars.get(tree.children[0]), tree.children[0]

    def func_call(self, tree: lark.tree.Tree) -> str:
        expr_type: _Type = _Type(_BaseType.ANY)

        code_strs: list[str] = list()
        arg_types: list[_Type] = list()
        for c in tree.children[1:]:
            tn, code = self.visit(c)
            code_strs.append(code)
            arg_types.append(tn)

        if tree.children[0] not in self._fns_ret_types:
            self._set_err_string('Function not in scope')
        else:
            expr_type = self._fns_ret_types.get(tree.children[0])
            if len(self._fns_params.get(tree.children[0])) != len(arg_types):
                self._set_err_string('Number of function parameters and given arguments must match')
            else:
                for tp, ta in zip(self._fns_params.get(tree.children[0]), arg_types):
                    if tp != ta:
                        self._set_err_string('Mismatched types in function call argument')
                        break

        return expr_type, f"{tree.children[0]}({', '.join(code_strs)})"

    def control_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):

        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'{self._indent_str}if({code}){{')

        self._new_scope()
        end_ind: int = 1
        for c in tree.children[1:]:
            if c.data != 'instruction':
                break
            end_ind += 1
            self.visit(c)
        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

        for c in tree.children[end_ind:]:
            self.visit(c)

    def elif_flow(self, tree: lark.tree.Tree):

        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'{self._indent_str}elif({code}){{')

        self._new_scope()
        for c in tree.children[1:]:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def else_flow(self, tree: lark.tree.Tree):
        self._html_buffer.write(f'{self._indent_str}else {{\n')

        self._new_scope()
        for c in tree.children:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def unless_flow(self, tree: lark.tree.Tree):

        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'{self._indent_str}unless({code}){{')

        self._new_scope()
        for c in tree.children[1:]:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def case_flow(self, tree: lark.tree.Tree):

        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.INT and tn.base != _BaseType.STRING:
            self._set_err_string('Type of case expression must be int or string')

        self._flush_err_string(f'{self._indent_str}case({code}){{')
        self._new_scope()
        for c in tree.children[1:]:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def of_flow(self, tree: lark.tree.Tree):

        _, code = self.visit(tree.children[0])
        self._html_buffer.write(f'{self._indent_str}of({code}){{\n')

        self._new_scope()
        for c in tree.children[1:]:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def default_flow(self, tree: lark.tree.Tree):

        self._html_buffer.write(f'{self._indent_str}default {{\n')

        self._new_scope()
        for c in tree.children:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def loop_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def while_flow(self, tree: lark.tree.Tree):

        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._flush_err_string(f'{self._indent_str}while({code}){{')

        self._new_scope()
        for c in tree.children[1:]:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def do_while_flow(self, tree: lark.tree.Tree):

        self._html_buffer.write(f'{self._indent_str}do {{\n')

        self._new_scope()
        for c in tree.children[0:-1]:
            self.visit(c)

        tn, code = self.visit(tree.children[-1])
        if tn.base != _BaseType.BOOL:
            self._set_err_string('Type of condition expression must be bool')

        self._end_scope()
        self._flush_err_string(f'{self._indent_str}}} while({code});')

    def for_flow(self, tree: lark.tree.Tree):
        self._new_scope()

        tn, code = self.visit(tree.children[1])
        if tn.base == _BaseType.ARRAY:
            self._add_var(tree.children[0], tn.typename[0])
        elif tn.base == _BaseType.LIST:
            self._add_var(tree.children[0], tn.typename)
        else:
            self._set_err_string('Type of expression must iterable')

        self._flush_err_string(f'{self._indent_str[:-4]}for({tree.children[0]} in {code}){{')

        for c in tree.children[2:]:
            self.visit(c)

        self._end_scope()
        self._html_buffer.write(f'{self._indent_str}}}\n')

    def read(self, tree: lark.tree.Tree) -> (_Type, str):
        return _Type(_BaseType.ANY), 'read()'

    def write(self, tree: lark.tree.Tree):
        code_strs: list[str] = list()
        for c in tree.children:
            _, code = self.visit(c)
            code_strs.append(code)
        self._flush_err_string(
            f"{self._indent_str}write({', '.join(code_strs)});"
        )

    def head(self, tree: lark.tree.Tree) -> (_Type, str):
        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.LIST:
            self._set_err_string('head() operations can be only be used on lists')
        return tn.typename, f"head({code})"

    def tail(self, tree: lark.tree.Tree) -> (_Type, str):
        tn, code = self.visit(tree.children[0])
        if tn.base != _BaseType.LIST:
            self._set_err_string('tail() operations can be only be used on lists')
        return tn, f"tail({code})"

    def literal(self, tree: lark.tree.Tree) -> (_Type, str):
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])
        else:
            return _Type(_BaseType.BOOL), tree.children[0]

    def int_literal(self, tree: lark.tree.Tree) -> (_Type, str):
        return _Type(_BaseType.INT), tree.children[0]

    def string_literal(self, tree: lark.tree.Tree) -> (_Type, str):
        return _Type(_BaseType.STRING), tree.children[0]

    def float_literal(self, tree: lark.tree.Tree) -> (_Type, str):
        return _Type(_BaseType.FLOAT), tree.children[0]

    def list_literal(self, tree: lark.tree.Tree) -> (_Type, str):
        if len(tree.children) == 0:
            return _Type(_BaseType.LIST, _Type(_BaseType.ANY)), '[]'

        tn0, code0 = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            tn, code = self.visit(c)
            code_strs.append(code)
            if tn0 != tn:
                self._set_err_string('Lists must have homogeneous types')

        return (
            _Type(_BaseType.LIST, tn0),
            f"[{', '.join(code_strs)}]"
        )

    def array_literal(self, tree: lark.tree.Tree) -> (_Type, str):
        tn0, code0 = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            tn, code = self.visit(c)
            code_strs.append(code)
            if tn0 != tn:
                self._set_err_string('Arrays must have homogeneous types')

        return (
            _Type(_BaseType.ARRAY, (tn0, len(tree.children))),
            f"{{{', '.join(code_strs)}}}"
        )

    def tuple_literal(self, tree: lark.tree.Tree) -> (_Type, str):
        typenames: list[_Type] = list()
        code_strs: list[str] = list()
        for c in tree.children:
            tn, code = self.visit(c)
            typenames.append(tn)
            code_strs.append(code)

        return (
            _Type(_BaseType.TUPLE, tuple(typenames)),
            f"|{', '.join(code_strs)}|"
        )
