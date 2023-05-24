_KEYWORDS: frozenset[str] = frozenset(
    [
        'fn', 'let', 'return', 'int', 'bool', 'string',
        'float', 'tuple', 'array', 'list', 'read', 'write',
        'if', 'else', 'elif', 'unless',
        'case', 'of', 'default'
        'while', 'for', 'do', 'in', 'head', 'tail'
        'true', 'false'
    ]
)

GRAMMAR: str = f'''
unit           : construct*
construct      : func_defn
               | var_defn

func_defn      : "fn" CONSTRUCT_ID func_params ("->" type)? "{{" instruction* "}}"
func_params    : "(" (var_bind ("," var_bind)*)? ")"

var_defn       : "let" var_bind "=" expression ";"

var_bind       : CONSTRUCT_ID ":" type

instruction    : var_defn
               | ret
               | write
               | control_flow
               | attrib
               | func_call ";"

ret            : "return" expression? ";"

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
               | read
               | head
               | tail
               | literal
               | func_call
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
if_flow        : "if" "(" expression ")" "{{" instruction* "}}" elif_flow* else_flow?
elif_flow      : "elif" "(" expression ")" "{{" instruction* "}}"
else_flow      : "else" "{{" instruction* "}}"
unless_flow    : "unless" "(" expression ")" "{{" instruction* "}}"
case_flow      : "case" "(" expression ")" "{{" of_flow* default_flow "}}"
of_flow        : "of" "(" (int_literal|string_literal) ")" "{{" instruction* "}}"
default_flow   : "default" "{{" instruction* "}}"


loop_flow      : while_flow
               | do_while_flow
               | for_flow
while_flow     : "while" "(" expression ")" "{{" instruction* "}}"
do_while_flow  : "do" "{{" instruction* "}}" "while" "(" expression ")" ";"
for_flow       : "for" "(" CONSTRUCT_ID "in" expression ")" "{{" instruction* "}}"


read           : "read" "(" ")"
write          : "write" "(" expression ("," expression)* ")" ";"

head           : "head" "(" expression ")"
tail           : "tail" "(" expression ")"

CONSTRUCT_ID   : /\\b(?!({'|'.join(_KEYWORDS)})\\b)[_A-Za-z][_A-Za-z0-9]*\\b/

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
list_literal   : "["  (expression ("," expression)*)? "]"
array_literal  : "{{"  expression ("," expression)* "}}"
tuple_literal  : "|"   expression ("," expression)+ "|"

%import common.WS
%import common.ESCAPED_STRING -> STRING
%ignore WS
'''
