#include <stdio.h>
#include <time.h>

static void print_probe_plan(void)
{
    puts("aurora-pi-hardwared: Raspberry Pi hardware service starting");
    puts("probe: /proc/device-tree/model");
    puts("probe: gpiochip devices");
    puts("probe: i2c buses");
    puts("probe: spi buses");
    puts("probe: serial UARTs");
    puts("probe: thermal zones");
}

int main(void)
{
    time_t now = time(NULL);
    print_probe_plan();
    printf("service-time: %ld\n", (long)now);
    puts("status: scaffold ready; DBus API implementation next");
    return 0;
}
