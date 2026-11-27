#include "gpu" // builtin by builtins/
#include "std" // builtin from compiler: #symbol, std::, ...
show_money(money) {
    gpu::write(std::strint(money), 94, 0)
    gpu::write("$", 96, 0)
    return
}

main() {
    money = 0
    x = 200
    gpu::create(x, 100);
    gpu::write("Hello World", 0, 0);
    show_money(money)
    gpu::show();
    sleep(300)
    money+=30
    show_money(money)
    gpu::show();
    return 0;
}