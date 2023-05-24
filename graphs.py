import lark
import typing
#import io
import pydot


class GraphInterpreter(lark.visitors.Interpreter):

    _node_id: int
    _parent_id: typing.Optional[int]
    _edge_color: typing.Optional[str]
    _is_fn_scope: bool
    _graph: pydot.Dot

    def __init__(self):
        self._node_id = 0
        self._parent_id = None
        self._is_fn_scope = False
        self._graph = pydot.Dot('F', graph_type='digraph')

    def _next_id(self):
        self._node_id += 1
        return self._node_id

    def _add_node(self, node_id: int, label: str, shape: str = 'oval', fc: str = None):
        node: pydot.Node = None
        if fc is not None:
            node = pydot.Node(
                f'node{node_id}',
                label=label,
                shape=shape,
                fillcolor=fc,
                style='filled'
            )
        else:
            node = pydot.Node(
                f'node{node_id}',
                label=label,
                shape=shape
            )
        self._graph.add_node(node)

    def _add_edge(self, child_id: str):
        edge: pydot.Edge = None
        if self._edge_color is not None:
            edge = pydot.Edge(
                f'node{self._parent_id}',
                f'node{child_id}',
                color=self._edge_color
            )
        else:
            edge = pydot.Edge(
                f'node{self._parent_id}',
                f'node{child_id}'
            )
        self._graph.add_edge(edge)

    def get_dot_str(self) -> str:
        return self._graph.to_string()

    #def unit(self, tree: lark.tree.Tree):
    #    for c in tree.children:
    #        self.visit(c)
    #    self._html_buffer.write('</pre></div></body></html>')

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):

        self._is_fn_scope = True

        params_code = self.visit(tree.children[1])

        type_code: str = ''
        inst_ind: int = 2
        if len(tree.children) > 2 and tree.children[2].data == 'type':
            inst_ind += 1
            code = self.visit(tree.children[2])
            type_code: str = f" -> {code}"

        this_id: int = self._next_id()
        self._parent_id = this_id
        self._add_node(this_id, f'{tree.children[0]}{params_code}{type_code}')

        for c in tree.children[inst_ind:]:
            self.visit(c)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end fn&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)
        self._is_fn_scope = False

    def func_params(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()

        for c in tree.children:
            bind_code = self.visit(c)
            code_strs.append(bind_code)

        return f"({', '.join(code_strs)})"

    def var_defn(self, tree: lark.tree.Tree):
        if not self._is_fn_scope:
            return

        bind_code = self.visit(tree.children[0])
        expr_code = self.visit(tree.children[1])

        this_id: int = self._next_id()
        self._add_node(this_id, f"{bind_code} = {expr_code}")
        self._add_edge(self._node_id)
        self._edge_color = None
        self._parent_id = this_id

    def var_bind(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[1])
        return f"{tree.children[0]}: {code}"

    def instruction(self, tree: lark.tree.Tree):
        if ret := self.visit(tree.children[0]):
            this_id: int = self._next_id()
            self._add_node(this_id, f"{ret[1]};")
            self._add_edge(self._node_id)
            self._parent_id = this_id

    def ret(self, tree: lark.tree.Tree):
        return
        #if len(tree.children) == 1:
        #    code = self.visit(tree.children[0])
        #    self._flush_err_string(f'return {code};')
        #else:
        #    self._flush_err_string(f'return;')

    def attrib(self, tree: lark.tree.Tree):
        var: str = tree.children[0]
        expr_code: str = self.visit(tree.children[-1])
        this_id: int = self._next_id()

        if len(tree.children) == 2:
            self._add_node(this_id, f'{var} = {expr_code}', 'rectangle')
        else:
            ind_code: str = self.visit(tree.children[1])
            self._add_node(
                this_id,
                f'{var}[{ind_code}] = {expr_code};',
                'rectangle'
            )
        self._add_edge(self._node_id)
        self._edge_color = None
        self._parent_id = this_id

    def type(self, tree: lark.tree.Tree) -> str:
        if isinstance(tree.children[0], lark.lexer.Token):  # primitive type
            return tree.children[0]
        else:
            return self.visit(tree.children[0])

    def tuple_t(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()
        for c in tree.children:
            code = self.visit(c)
            code_strs.append(code)

        return f"tuple<{', '.join(code_strs)}>"

    def array_t(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[0])
        size = self.visit(tree.children[1])
        return f"array<{code}, {size}>"

    def list_t(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[0])
        return f"list<{code}>"

    def expression(self, tree: lark.tree.Tree) -> str:
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])

    def plus_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} + {code_rhs}"

    def minus_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} - {code_rhs}"

    def mul_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} * {code_rhs}"

    def div_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} / {code_rhs}"

    def mod_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} % {code_rhs}"

    def exp_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} ^ {code_rhs}"

    def prepend_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} ^: {code_rhs}"

    def append_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} $: {code_rhs}"

    def eq_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} == {code_rhs}"

    def neq_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} != {code_rhs}"

    def and_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} && {code_rhs}"

    def or_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs = self.visit(tree.children[0])
        code_rhs = self.visit(tree.children[1])
        return f"{code_lhs} || {code_rhs}"

    def not_expr(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[0])
        return f"!{code}"

    def paren_expr(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[0])
        return f"({code})"

    def var_deref(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 2:
            code = self.visit(tree.children[1])
            return f"{tree.children[0]}[{code}]"
        else:
            return tree.children[0]

    def func_call(self, tree: lark.tree.Tree) -> str:

        code_strs: list[str] = list()
        for c in tree.children[1:]:
            code = self.visit(c)
            code_strs.append(code)

        return f"{tree.children[0]}({', '.join(code_strs)})"

    def control_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):
        code = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'if({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = 'green'

        end_ind: int = 1
        for c in tree.children[1:]:
            if c.data != 'instruction':
                break
            end_ind += 1
            self.visit(c)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end if&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        # elif, else
        if end_ind < len(tree.children):
            for c in tree.children[end_ind:]:
                self._edge_color = 'red'
                self._parent_id = this_id
                self.visit(c)
                self._add_edge(dummy_id)
        else:
            self._edge_color = 'red'
            self._parent_id = this_id
            self._add_edge(dummy_id)

        self._edge_color = None
        self._parent_id = dummy_id

    def elif_flow(self, tree: lark.tree.Tree):
        return
        code = self.visit(tree.children[0])

        self._flush_err_string(f'elif({code}){{')

        for c in tree.children[1:]:
            self.visit(c)

        self._html_buffer.write('}\n')

    def else_flow(self, tree: lark.tree.Tree):
        for c in tree.children:
            self.visit(c)

    def unless_flow(self, tree: lark.tree.Tree):
        code = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'unless({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = 'red'

        end_ind: int = 1
        for c in tree.children[1:]:
            if c.data != 'instruction':
                break
            end_ind += 1
            self.visit(c)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end unless&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        self._edge_color = 'green'
        self._parent_id = this_id
        self._add_edge(dummy_id)

        self._edge_color = None
        self._parent_id = dummy_id

        return
        code = self.visit(tree.children[0])

        self._flush_err_string(f'unless({code}){{')

        for c in tree.children[1:]:
            self.visit(c)

        self._html_buffer.write('}\n')

    def case_flow(self, tree: lark.tree.Tree):
        return

        code = self.visit(tree.children[0])

        self._flush_err_string(f'case({code}){{')
        for c in tree.children[1:]:
            self.visit(c)

        self._html_buffer.write('}\n')

    def of_flow(self, tree: lark.tree.Tree):
        return
        code = self.visit(tree.children[0])
        self._html_buffer.write(f'of({code}){{\n')

        for c in tree.children[1:]:
            self.visit(c)

        self._html_buffer.write('}\n')

    def default_flow(self, tree: lark.tree.Tree):
        return
        self._html_buffer.write('default {\n')

        for c in tree.children:
            self.visit(c)

        self._html_buffer.write('}\n')

    def loop_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def while_flow(self, tree: lark.tree.Tree):
        code = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'while({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id

        for c in tree.children[1:]:
            self.visit(c)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end while&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        self._parent_id = dummy_id
        self._add_edge(this_id)

    def do_while_flow(self, tree: lark.tree.Tree):
        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;begin do-while&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        self._parent_id = dummy_id

        for c in tree.children[0:-1]:
            self.visit(c)

        code = self.visit(tree.children[-1])

        this_id: int = self._next_id()
        self._add_node(this_id, f'while({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._add_edge(dummy_id)

    def for_flow(self, tree: lark.tree.Tree):
        code = self.visit(tree.children[1])

        this_id: int = self._next_id()
        self._add_node(this_id, f'for({tree.children[0]} in {code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id

        for c in tree.children[1:]:
            self.visit(c)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end for&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        self._parent_id = dummy_id
        self._add_edge(this_id)

    def read(self, tree: lark.tree.Tree) -> str:
        return 'read()'

    def write(self, tree: lark.tree.Tree):
        code_strs: list[str] = list()
        for c in tree.children:
            code = self.visit(c)
            code_strs.append(code)

        this_id: int = self._next_id()
        self._add_node(this_id, f"write({', '.join(code_strs)})", 'rectangle')
        self._add_edge(this_id)
        self._parent_id = this_id

    def head(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[0])
        return f"head({code})"

    def tail(self, tree: lark.tree.Tree) -> str:
        code = self.visit(tree.children[0])
        return f"tail({code})"

    def literal(self, tree: lark.tree.Tree) -> str:
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])
        else:
            return tree.children[0]

    def int_literal(self, tree: lark.tree.Tree) -> str:
        return tree.children[0]

    def string_literal(self, tree: lark.tree.Tree) -> str:
        return tree.children[0]

    def float_literal(self, tree: lark.tree.Tree) -> str:
        return tree.children[0]

    def list_literal(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 0:
            return '[]'

        code0 = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            code = self.visit(c)
            code_strs.append(code)

        return f"[{', '.join(code_strs)}]"

    def array_literal(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 0:
            return r'{}'

        code0 = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            code = self.visit(c)
            code_strs.append(code)

        return f"{{{', '.join(code_strs)}}}"

    def tuple_literal(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()
        for c in tree.children:
            code = self.visit(c)
            code_strs.append(code)

        return f"|{', '.join(code_strs)}|"
