let y: bool = true;

fn foo(var: int, baz: string) {
    let x: float = 3.0;

    if(true != false){
        x = 2.0;
    }

    x = 4.5;

    if(3 == 4){
        let n: int = 2;

        if(true && false){
            let t: tuple<string, int> = |"", 0|;
        }
    }
    else {
    }

    let n: string = "";
}

fn bar() -> tuple<int, float> {
    let i: array<int, 4> = {};
    case(1+1){
        of(1){ }
        of(2){ }
        default { }
    }

    while(true){ }

    for(a in [1,2,3]){ write("\n"); }

    return |1+1, 2.0+2.0|;
}
