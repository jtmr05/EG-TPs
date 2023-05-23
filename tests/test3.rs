let foo: string = "cena\"1\"";

fn bar(a: int) -> float {
    let f: string = foo + "\n";
    return (1.0 * 2.0);
}

fn foo() -> tuple<array<string, 4>, bool> {
    let b: float = bar(1+2*3^4);
    let c: float = bar(1+2*3^4, "foo");
    let d: float = bar("foo");
    let d: float = 1.0;
    e = 12;

    let input: string = "";
    let inputs: array<string, 4> = {};
    for(a in {0,1,2}){
        let line: string = read();
        inputs[a] = line;
    }
    write(inputs, b, c, (1+2+3)*4 % 5, bar(-1));
    return |inputs, false|;
}

fn baz() -> int {
    let i: int = 0;
    let l: list<int> = [1,2,3,4,5,6,7];
    let s: list<string> = [];
    while(i != 5){
        i = i + 1;
        let h: int = head(l);
        write(h);
        l = tail(l);
        s = l;
        unless(h % 2 == 0){
            return;
        }
    }
}

fn foo() -> int {
    let f: float = "";
    let arr: array<string, 4> = {"ccc", "", ""};
    b[2] = "";
    f[1] = 3;
    arr[1] = 1;
    arr[""] = "cena";
    let boolean: bool = [1] + [];
    let i: int = 1 - 1;
    let t: int = "" - "";
    let x: int = 1.0 - 3;
    let y: int = 1.0 * 3;

    let num_list: list<int> = [];
    for(elem in [1,2,3,4,5]){
        num_list = elem ^: elem;
        num_list = num_list $: num_list;
    }

    if(1 && 2){ }

    unless(2 || 4){
    }

    while(!"string"){
    }

    return arr___[1];
    return f[1];
    return arr[""];
    return head(f);
    return tail(f);

    let another_list: list<string> = ["", 1];
    let another_array: array<string, 2> = {"", 1};

    do {
        write(f);
    } while(f != 1.0);
}
