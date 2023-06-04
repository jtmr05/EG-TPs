import lark
import typing
import pydot


class CFGraphInterpreter(lark.visitors.Interpreter):

    _node_id: int
    _parent_id: typing.Optional[int]
    _edge_color: typing.Optional[str]
    _is_dead_edge: bool
    _is_fn_scope: bool
    _fn_to_graph: dict[str, pydot.Dot]
    _curr_fn: str

    def __init__(self):
        self._node_id = 0
        self._parent_id = None
        self._edge_color = None
        self._is_dead_edge = False
        self._is_fn_scope = False
        self._fn_to_graph = dict()
        self._curr_fn = ''

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
        self._fn_to_graph[self._curr_fn].add_node(node)

    def _add_edge(self, child_id: str):
        if self._parent_id is None:
            return

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
        if self._is_dead_edge:
            edge.set('style', 'dashed')
            edge.set('label', 'dead code!')
            edge.set('color', 'gray')
            edge.set('fillcolor', 'gray')

        self._fn_to_graph[self._curr_fn].add_edge(edge)
        self._is_dead_edge = False

    def get_func_name_graph_pairs(self) -> list[tuple[str, pydot.Dot]]:
        return list(self._fn_to_graph.items())

    def _compute_mccabes_complexity(self) -> int:
        graph: pydot.Dot = self._fn_to_graph[self._curr_fn]
        nodes: list[pydot.Node] = graph.get_nodes()
        edges: list[pydot.Edge] = graph.get_edges()
        return len(edges) - len(nodes) + 2

    ###############

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):
        self._curr_fn = tree.children[0]
        self._fn_to_graph[self._curr_fn] = pydot.Dot('F', graph_type='digraph')
        self._is_fn_scope = True

        params_code: str = self.visit(tree.children[1])

        type_code: str = ''
        inst_ind: int = 2
        if len(tree.children) > 2 and tree.children[2].data == 'type':
            inst_ind += 1
            code: str = self.visit(tree.children[2])
            type_code = f" -> {code}"

        this_id: int = self._next_id()
        self._parent_id = this_id
        self._add_node(this_id, f'{tree.children[0]}{params_code}{type_code}', fc='#c8f771')

        for c in tree.children[inst_ind:]:
            self.visit(c)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end fn&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        mccabes_complexity: int = self._compute_mccabes_complexity()
        self._add_node('complex', f"McCabe's complexity: {mccabes_complexity}", 'plaintext')

        self._is_fn_scope = False

    def func_params(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()

        for c in tree.children:
            bind_code: str = self.visit(c)
            code_strs.append(bind_code)

        return f"({', '.join(code_strs)})"

    def var_defn(self, tree: lark.tree.Tree):
        if not self._is_fn_scope:
            return

        bind_code: str = self.visit(tree.children[0])
        expr_code: str = self.visit(tree.children[1])

        this_id: int = self._next_id()
        self._add_node(this_id, f"{bind_code} = {expr_code}")
        self._add_edge(self._node_id)
        self._edge_color = None
        self._parent_id = this_id

    def var_bind(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[1])
        return f"{tree.children[0]}: {code}"

    def instruction(self, tree: lark.tree.Tree):
        if tree.children[0].data != 'func_call':
            self.visit(tree.children[0])

    def ret(self, tree: lark.tree.Tree):
        this_id: int = self._next_id()
        if len(tree.children) == 1:
            code: str = self.visit(tree.children[0])
            self._add_node(this_id, f'return {code}', 'rectangle', '#e085dd')
        else:
            self._add_node(this_id, 'return', 'rectangle', '#e085dd')
        self._add_edge(self._node_id)
        self._edge_color = None
        self._is_dead_edge = True
        self._parent_id = this_id

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
            code: str = self.visit(c)
            code_strs.append(code)

        return f"tuple<{', '.join(code_strs)}>"

    def array_t(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        size: str = self.visit(tree.children[1])
        return f"array<{code}, {size}>"

    def list_t(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"list<{code}>"

    def expression(self, tree: lark.tree.Tree) -> str:
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])

    def plus_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} + {code_rhs}"

    def minus_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} - {code_rhs}"

    def mul_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} * {code_rhs}"

    def div_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} / {code_rhs}"

    def mod_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} % {code_rhs}"

    def exp_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} ^ {code_rhs}"

    def prepend_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} ^: {code_rhs}"

    def append_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} $: {code_rhs}"

    def eq_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} == {code_rhs}"

    def neq_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} != {code_rhs}"

    def and_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} && {code_rhs}"

    def or_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} || {code_rhs}"

    def not_expr(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"!{code}"

    def paren_expr(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"({code})"

    def var_deref(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 2:
            code: str = self.visit(tree.children[1])
            return f"{tree.children[0]}[{code}]"
        else:
            return tree.children[0]

    def func_call(self, tree: lark.tree.Tree):
        pass
        #code_strs: list[str] = list()
        #for c in tree.children[1:]:
        #    code: str = self.visit(c)
        #    code_strs.append(code)

        #return f"{tree.children[0]}({', '.join(code_strs)})"

    def control_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):
        code: str = self.visit(tree.children[0])

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
                this_id = self.visit(c)
                self._add_edge(dummy_id)
        else:
            self._edge_color = 'red'
            self._parent_id = this_id
            self._add_edge(dummy_id)

        self._edge_color = None
        self._parent_id = dummy_id

    def elif_flow(self, tree: lark.tree.Tree) -> int:
        code: str = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'elif({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = 'green'

        for c in tree.children[1:]:
            self.visit(c)

        return this_id

    def else_flow(self, tree: lark.tree.Tree):
        for c in tree.children:
            self.visit(c)
            self._edge_color = None

    def unless_flow(self, tree: lark.tree.Tree):
        code: str = self.visit(tree.children[0])

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

    def case_flow(self, tree: lark.tree.Tree):
        code: str = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'case({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = None

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end case&gt;', 'diamond', 'gray')

        for c in tree.children[1:]:
            self._parent_id = this_id
            self.visit(c)
            self._add_edge(dummy_id)

        self._parent_id = dummy_id

    def of_flow(self, tree: lark.tree.Tree):
        code: str = self.visit(tree.children[0])
        this_id: int = self._next_id()
        self._add_node(this_id, f'of({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id

        for c in tree.children[1:]:
            self.visit(c)

    def default_flow(self, tree: lark.tree.Tree):
        this_id: int = self._next_id()
        self._add_node(this_id, 'default', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id

        for c in tree.children:
            self.visit(c)

    def loop_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def while_flow(self, tree: lark.tree.Tree):
        code: str = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'while({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = 'green'

        for c in tree.children[1:]:
            self.visit(c)

        self._add_edge(this_id)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end while&gt;', 'diamond', 'gray')
        self._parent_id = this_id
        self._edge_color = 'red'
        self._add_edge(dummy_id)

        self._edge_color = None
        self._parent_id = dummy_id

    def do_while_flow(self, tree: lark.tree.Tree):
        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;begin do-while&gt;', 'diamond', 'gray')
        self._add_edge(dummy_id)

        self._parent_id = dummy_id

        for c in tree.children[0:-1]:
            self.visit(c)

        code: str = self.visit(tree.children[-1])

        this_id: int = self._next_id()
        self._add_node(this_id, f'while({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = 'green'
        self._add_edge(dummy_id)

        self._edge_color = 'red'

    def for_flow(self, tree: lark.tree.Tree):
        code: str = self.visit(tree.children[1])

        this_id: int = self._next_id()
        self._add_node(this_id, f'for({tree.children[0]} in {code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._edge_color = 'green'

        for c in tree.children[2:]:
            self.visit(c)

        self._add_edge(this_id)

        dummy_id: int = self._next_id()
        self._add_node(dummy_id, '&lt;end for&gt;', 'diamond', 'gray')
        self._parent_id = this_id
        self._edge_color = 'red'
        self._add_edge(dummy_id)

        self._edge_color = None
        self._parent_id = dummy_id

    def read(self, tree: lark.tree.Tree) -> str:
        return 'read()'

    def write(self, tree: lark.tree.Tree):
        code_strs: list[str] = list()
        for c in tree.children:
            code: str = self.visit(c)
            code_strs.append(code)

        this_id: int = self._next_id()
        self._add_node(this_id, f"write({', '.join(code_strs)})", 'rectangle')
        self._add_edge(this_id)
        self._edge_color = None
        self._parent_id = this_id

    def head(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"head({code})"

    def tail(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
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

        code0: str = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"[{', '.join(code_strs)}]"

    def array_literal(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 0:
            return r'{}'

        code0: str = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"{{{', '.join(code_strs)}}}"

    def tuple_literal(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()
        for c in tree.children:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"|{', '.join(code_strs)}|"


class SDGraphInterpreter(lark.visitors.Interpreter):

    _node_id: int
    _parent_id: typing.Optional[int]
    _is_dead_code: bool
    _is_fn_scope: bool
    _fn_to_graph: dict[str, pydot.Dot]
    _curr_fn: str
    _curr_subgraph: pydot.Subgraph

    def __init__(self):
        self._node_id = 0
        self._parent_id = None
        self._is_dead_code = False
        self._is_fn_scope = False
        self._fn_to_graph = dict()
        self._curr_fn = ''
        self._curr_subgraph = None

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

        if self._is_dead_code:
            self._curr_subgraph.add_node(node)
        else:
            self._fn_to_graph[self._curr_fn].add_node(node)

    def _add_edge(self, child_id: str):
        if self._parent_id is None:
            return

        edge: pydot.Edge = pydot.Edge(
            f'node{self._parent_id}',
            f'node{child_id}'
        )

        self._fn_to_graph[self._curr_fn].add_edge(edge)

    def get_func_name_graph_pairs(self) -> list[tuple[str, pydot.Dot]]:
        return list(self._fn_to_graph.items())

    def _compute_mccabes_complexity(self) -> int:
        graph: pydot.Dot = self._fn_to_graph[self._curr_fn]
        nodes: list[pydot.Node] = graph.get_nodes()
        edges: list[pydot.Edge] = graph.get_edges()
        return len(edges) - len(nodes) + 2

    ###############

    def construct(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def func_defn(self, tree: lark.tree.Tree):
        self._curr_fn = tree.children[0]
        self._fn_to_graph[self._curr_fn] = pydot.Dot('F', graph_type='digraph')
        self._fn_to_graph[self._curr_fn].set('rankdir', 'LR')
        self._curr_subgraph = pydot.Subgraph('cluster_box')
        self._curr_subgraph.set('style', 'filled')
        self._curr_subgraph.set('label', 'Dead code')
        self._curr_subgraph.set('color', 'lightgray')
        self._is_fn_scope = True

        params_code: str = self.visit(tree.children[1])

        type_code: str = ''
        inst_ind: int = 2
        if len(tree.children) > 2 and tree.children[2].data == 'type':
            inst_ind += 1
            code: str = self.visit(tree.children[2])
            type_code = f" -> {code}"

        this_id: int = self._next_id()
        self._parent_id = this_id
        self._add_node(this_id, f'{tree.children[0]}{params_code}{type_code}', fc='#c8f771')

        for c in tree.children[inst_ind:]:
            if self.visit(c):
                break
        #else:
        #    dummy_id: int = self._next_id()
        #    self._add_node(dummy_id, 'return', 'rectangle', '#e085dd')
        #    self._add_edge(dummy_id)

        self._fn_to_graph[self._curr_fn].add_subgraph(self._curr_subgraph)

        self._is_fn_scope = False
        self._is_dead_code = False

        mccabes_complexity: int = self._compute_mccabes_complexity()
        self._add_node('complex', f"McCabe's complexity: {mccabes_complexity}", 'plaintext')

    def func_params(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()

        for c in tree.children:
            bind_code: str = self.visit(c)
            code_strs.append(bind_code)

        return f"({', '.join(code_strs)})"

    def var_defn(self, tree: lark.tree.Tree):
        if not self._is_fn_scope:
            return

        bind_code: str = self.visit(tree.children[0])
        expr_code: str = self.visit(tree.children[1])

        this_id: int = self._next_id()
        self._add_node(this_id, f"{bind_code} = {expr_code}")
        self._add_edge(self._node_id)

    def var_bind(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[1])
        return f"{tree.children[0]}: {code}"

    def instruction(self, tree: lark.tree.Tree) -> bool:
        if ret := self.visit(tree.children[0]):
            this_id: int = self._next_id()
            self._add_node(this_id, f"{ret}")
            self._add_edge(self._node_id)
            return False
        return False  # tree.children[0].data == 'ret'

    def ret(self, tree: lark.tree.Tree):
        this_id: int = self._next_id()
        if len(tree.children) == 1:
            code: str = self.visit(tree.children[0])
            self._add_node(this_id, f'return {code}', 'rectangle', '#e085dd')
        else:
            self._add_node(this_id, 'return', 'rectangle', '#e085dd')
        self._add_edge(self._node_id)
        self._is_dead_code = True

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

    def type(self, tree: lark.tree.Tree) -> str:
        if isinstance(tree.children[0], lark.lexer.Token):  # primitive type
            return tree.children[0]
        else:
            return self.visit(tree.children[0])

    def tuple_t(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()
        for c in tree.children:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"tuple<{', '.join(code_strs)}>"

    def array_t(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        size: str = self.visit(tree.children[1])
        return f"array<{code}, {size}>"

    def list_t(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"list<{code}>"

    def expression(self, tree: lark.tree.Tree) -> str:
        if isinstance(tree.children[0], lark.tree.Tree):
            return self.visit(tree.children[0])

    def plus_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} + {code_rhs}"

    def minus_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} - {code_rhs}"

    def mul_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} * {code_rhs}"

    def div_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} / {code_rhs}"

    def mod_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} % {code_rhs}"

    def exp_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} ^ {code_rhs}"

    def prepend_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} ^: {code_rhs}"

    def append_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} $: {code_rhs}"

    def eq_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} == {code_rhs}"

    def neq_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} != {code_rhs}"

    def and_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} && {code_rhs}"

    def or_expr(self, tree: lark.tree.Tree) -> str:
        code_lhs: str = self.visit(tree.children[0])
        code_rhs: str = self.visit(tree.children[1])
        return f"{code_lhs} || {code_rhs}"

    def not_expr(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"!{code}"

    def paren_expr(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"({code})"

    def var_deref(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 2:
            code: str = self.visit(tree.children[1])
            return f"{tree.children[0]}[{code}]"
        else:
            return tree.children[0]

    def func_call(self, tree: lark.tree.Tree) -> str:

        code_strs: list[str] = list()
        for c in tree.children[1:]:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"{tree.children[0]}({', '.join(code_strs)})"

    def control_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def branch_flow(self, tree: lark.tree.Tree):
        self.visit(tree.children[0])

    def if_flow(self, tree: lark.tree.Tree):
        old_parent_id: int = self._parent_id
        is_dead_code: bool = self._is_dead_code  # store old value first

        code: str = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'if({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id

        end_ind: int = 1
        for c in tree.children[1:]:
            if c.data != 'instruction' or self.visit(c):
                break
            end_ind += 1

        self._is_dead_code = is_dead_code
        self._parent_id = old_parent_id

        for c in tree.children[end_ind:]:
            self.visit(c)

    def elif_flow(self, tree: lark.tree.Tree) -> int:
        old_parent_id: int = self._parent_id
        is_dead_code: bool = self._is_dead_code  # store old value first

        code: str = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'elif({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id

        for c in tree.children[1:]:
            if self.visit(c):
                break

        self._is_dead_code = is_dead_code
        self._parent_id = old_parent_id

    def else_flow(self, tree: lark.tree.Tree):
        old_parent_id: int = self._parent_id
        is_dead_code: bool = self._is_dead_code  # store old value first

        for c in tree.children:
            self.visit(c)

        self._is_dead_code = is_dead_code
        self._parent_id = old_parent_id

    def unless_flow(self, tree: lark.tree.Tree):
        pass

    def case_flow(self, tree: lark.tree.Tree):
        pass

    def loop_flow(self, tree: lark.tree.Tree):
        is_dead_code: bool = self._is_dead_code  # store old value first
        self.visit(tree.children[0])
        self._is_dead_code = is_dead_code

    def while_flow(self, tree: lark.tree.Tree):
        old_parent_id: int = self._parent_id

        code: str = self.visit(tree.children[0])

        this_id: int = self._next_id()
        self._add_node(this_id, f'while({code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._add_edge(this_id)

        for c in tree.children[1:]:
            if self.visit(c):
                break

        self._parent_id = old_parent_id

    def do_while_flow(self, tree: lark.tree.Tree):
        pass

    def for_flow(self, tree: lark.tree.Tree):
        old_parent_id: int = self._parent_id

        code: str = self.visit(tree.children[1])

        this_id: int = self._next_id()
        self._add_node(this_id, f'for({tree.children[0]} in {code})', 'diamond')
        self._add_edge(this_id)
        self._parent_id = this_id
        self._add_edge(this_id)

        for c in tree.children[2:]:
            if self.visit(c):
                break

        self._parent_id = old_parent_id

    def read(self, tree: lark.tree.Tree) -> str:
        return 'read()'

    def write(self, tree: lark.tree.Tree):
        old_parent_id: int = self._parent_id

        code_strs: list[str] = list()
        for c in tree.children:
            code: str = self.visit(c)
            code_strs.append(code)

        this_id: int = self._next_id()
        self._add_node(this_id, f"write({', '.join(code_strs)})", 'rectangle')
        self._add_edge(this_id)

        self._parent_id = old_parent_id

    def head(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
        return f"head({code})"

    def tail(self, tree: lark.tree.Tree) -> str:
        code: str = self.visit(tree.children[0])
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

        code0: str = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"[{', '.join(code_strs)}]"

    def array_literal(self, tree: lark.tree.Tree) -> str:
        if len(tree.children) == 0:
            return r'{}'

        code0: str = self.visit(tree.children[0])
        code_strs: list[str] = list()
        code_strs.append(code0)

        for c in tree.children[1:]:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"{{{', '.join(code_strs)}}}"

    def tuple_literal(self, tree: lark.tree.Tree) -> str:
        code_strs: list[str] = list()
        for c in tree.children:
            code: str = self.visit(c)
            code_strs.append(code)

        return f"|{', '.join(code_strs)}|"
