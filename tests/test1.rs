let y: bool = true;

fn baz() -> int {
    return 1;
}

fn foo(var: int, baz: string) {
    let x: float = 3.0;

    if(true != false){
        x = 2.0;
    }

    x = 4.5;

    return;
    if(3 == 4){
        let n: int = 2;

        if(true && false){
            let t: tuple<string, int> = |"", 0|;
        }

    }
    else {
        write("foo");
    }

    let n: string = "";
}

fn bar() -> tuple<list<int>, int> {

    let count: int = 39489;
    count = count * 2;
    return |[], 1|;
    count = 1;

    while(count != 0){
        count = count / 2;
        if(count % 2 != 0){
            count = count - 1;
        }
        elif(count % 3 != 0){
            baz();
        }
        elif(count % 4 != 0){
            count = count + 3 ^ 800;
            count = read() * count;
        }
        else {
            count = count * 3;
            let x: tuple<string, int> = |"foo", count|;
        }
        write(count);
    }

    let i: list<int> = [];
    let x: int = 0;
    let j: int = 2;
    do {
        j = j ^ 2;
        unless(j % 10 == 0){
            i = j $: i;
        }
        x = x + 1;
    }
    while(x != 100);


    for(a in i){
        a = a * read();
        a = 1;
    }

    case(x){

    of(1){
        write("idkdk");
    }

    of(2){
        write("idkdk");
    }

    of(3){
        write("sjsjskj");
    }

    default {
        let thing: int = 89;
    }
    }

    return |i, x|;
}
