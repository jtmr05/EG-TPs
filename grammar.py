#!/usr/bin/env python3

import lark
import sys
import typing


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
               | "array" "<" type ">"
               | "list"  "<" type ">"
expression     : "(" expression ")"
               | expression "+" expression
               | expression "-" expression
               | expression "*" expression
               | expression "/" expression
               | expression "%" expression
               | expression "^" expression
               | expression "^:" expression
               | expression "$:" expression
               | expression "==" expression
               | expression "!=" expression
               | expression "&&" expression
               | expression "||" expression
               | "!" expression
               | CONSTRUCT_ID "[" expression "]"
               | CONSTRUCT_ID
               | literal
               | func_call
               | read
               | head
               | tail
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
write          : "write" "(" (expression ("," expression)*)? ")" ";"
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
float_literal  : /-?[0-9]+(\.[0-9]+)/
list_literal   : "[" (expression ("," expression)*)? "]"
tuple_literal  : "(" expression ("," expression)+ ")"

%import common.WS
%ignore WS
'''


def annotate(src: typing.Any, *ansi_escape_codes: int) -> str:

    length: int = len(ansi_escape_codes)
    if length == 0:
        return str(src)

    import io
    str_buffer: io.StringIO = io.StringIO()

    str_buffer.write(f"\033[{ansi_escape_codes[0]}")
    for i in range(1, length):
        str_buffer.write(f";{ansi_escape_codes[i]}")
    str_buffer.write(f"m{str(src)}\033[0m")

    return str_buffer.getvalue()


def main() -> int:

    tests: list[str] = [
        '''
        let y: bool = true;

        fn foo(var: int, baz: string) -> array<list<tuple<int, string>>> {
            let x: float = 3.0;
            return 3 $: 1;
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
            let i: array<int> = [1,2,3,45];
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
            print(f"==> test '{annotate(t, 1)}' {annotate('passed', 32, 1)}!", file=sys.stderr)

        except lark.UnexpectedCharacters:
            print(f"==> test '{annotate(t, 1)}' {annotate('failed', 31, 1)}!", file=sys.stderr)

        except lark.GrammarError:
            print(f"==> test '{annotate(t, 1)}' {annotate('failed', 31, 1)}!", file=sys.stderr)

        print("\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
