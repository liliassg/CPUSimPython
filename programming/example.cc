#include "gpu"

main() {
    gpu::create(100, 100);
    gpu::write("Hello World", 0, 0);
    gpu::show();
    return 0;
}