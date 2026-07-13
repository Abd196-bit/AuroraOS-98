#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void put_byte(uint8_t *sector, size_t *offset, uint8_t value)
{
    if (*offset >= 510) {
        fprintf(stderr, "boot sector overflow\n");
        exit(1);
    }
    sector[(*offset)++] = value;
}

static void put_data(uint8_t *sector, size_t *offset, const uint8_t *data, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        put_byte(sector, offset, data[i]);
    }
}

static void put_word(uint8_t *sector, size_t *offset, uint16_t value)
{
    put_byte(sector, offset, (uint8_t)(value & 0xff));
    put_byte(sector, offset, (uint8_t)(value >> 8));
}

static void put_text(uint8_t *sector, size_t *offset, const char *text)
{
    put_data(sector, offset, (const uint8_t *)text, strlen(text) + 1);
}

static void patch_word(uint8_t *sector, size_t offset, uint16_t value)
{
    sector[offset] = (uint8_t)(value & 0xff);
    sector[offset + 1] = (uint8_t)(value >> 8);
}

static void patch_rel8(uint8_t *sector, size_t offset, size_t target)
{
    int rel = (int)target - (int)(offset + 1);
    if (rel < -128 || rel > 127) {
        fprintf(stderr, "rel8 out of range\n");
        exit(1);
    }
    sector[offset] = (uint8_t)rel;
}

static void patch_rel16(uint8_t *sector, size_t offset, size_t target)
{
    int rel = (int)target - (int)(offset + 2);
    if (rel < -32768 || rel > 32767) {
        fprintf(stderr, "rel16 out of range\n");
        exit(1);
    }
    patch_word(sector, offset, (uint16_t)rel);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s OUTPUT.img\n", argv[0]);
        return 1;
    }

    uint8_t sector[512] = {0};
    size_t off = 0;

    put_byte(sector, &off, 0xfa);                 /* cli */
    put_byte(sector, &off, 0x31); put_byte(sector, &off, 0xc0); /* xor ax, ax */
    put_byte(sector, &off, 0x8e); put_byte(sector, &off, 0xd8); /* mov ds, ax */
    put_byte(sector, &off, 0x8e); put_byte(sector, &off, 0xc0); /* mov es, ax */
    put_byte(sector, &off, 0x8e); put_byte(sector, &off, 0xd0); /* mov ss, ax */
    put_byte(sector, &off, 0xbc); put_word(sector, &off, 0x7c00); /* mov sp, 0x7c00 */
    put_byte(sector, &off, 0xfb);                 /* sti */

    /* Initialize COM1 for QEMU -nographic output. */
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03f9); /* mov dx, 0x3f9 */
    put_byte(sector, &off, 0x30); put_byte(sector, &off, 0xc0);   /* xor al, al */
    put_byte(sector, &off, 0xee);                                 /* out dx, al */
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03fb);
    put_byte(sector, &off, 0xb0); put_byte(sector, &off, 0x80);
    put_byte(sector, &off, 0xee);
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03f8);
    put_byte(sector, &off, 0xb0); put_byte(sector, &off, 0x03);
    put_byte(sector, &off, 0xee);
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03f9);
    put_byte(sector, &off, 0x30); put_byte(sector, &off, 0xc0);
    put_byte(sector, &off, 0xee);
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03fb);
    put_byte(sector, &off, 0xb0); put_byte(sector, &off, 0x03);
    put_byte(sector, &off, 0xee);
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03fa);
    put_byte(sector, &off, 0xb0); put_byte(sector, &off, 0xc7);
    put_byte(sector, &off, 0xee);
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03fc);
    put_byte(sector, &off, 0xb0); put_byte(sector, &off, 0x0b);
    put_byte(sector, &off, 0xee);

    put_byte(sector, &off, 0xb8); put_word(sector, &off, 0x0003); /* mov ax, 0x0003 */
    put_byte(sector, &off, 0xcd); put_byte(sector, &off, 0x10);   /* int 0x10 */
    put_byte(sector, &off, 0xbe);
    size_t message_addr_patch = off;
    put_word(sector, &off, 0);
    put_byte(sector, &off, 0xe8);
    size_t call_print_patch = off;
    put_word(sector, &off, 0);
    put_byte(sector, &off, 0xf4);                                 /* hlt */
    put_byte(sector, &off, 0xeb); put_byte(sector, &off, 0xfd);   /* jmp -3 */

    size_t print_loop = off;
    put_byte(sector, &off, 0xac);                                 /* lodsb */
    put_byte(sector, &off, 0x84); put_byte(sector, &off, 0xc0);   /* test al, al */
    put_byte(sector, &off, 0x74);
    size_t jz_done_patch = off;
    put_byte(sector, &off, 0);
    put_byte(sector, &off, 0x50);                                 /* push ax */
    put_byte(sector, &off, 0xb4); put_byte(sector, &off, 0x0e);   /* mov ah, 0x0e */
    put_byte(sector, &off, 0xbb); put_word(sector, &off, 0x0007); /* mov bx, 0x0007 */
    put_byte(sector, &off, 0xcd); put_byte(sector, &off, 0x10);   /* int 0x10 */
    put_byte(sector, &off, 0x58);                                 /* pop ax */
    put_byte(sector, &off, 0xe8);
    size_t call_serial_patch = off;
    put_word(sector, &off, 0);
    put_byte(sector, &off, 0xeb);
    size_t jmp_print_patch = off;
    put_byte(sector, &off, 0);
    size_t print_done = off;
    put_byte(sector, &off, 0xc3);                                 /* ret */

    size_t serial_putchar = off;
    put_byte(sector, &off, 0x50);                                 /* push ax */
    size_t serial_wait = off;
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03fd); /* mov dx, 0x3fd */
    put_byte(sector, &off, 0xec);                                 /* in al, dx */
    put_byte(sector, &off, 0xa8); put_byte(sector, &off, 0x20);   /* test al, 0x20 */
    put_byte(sector, &off, 0x74);
    size_t serial_wait_patch = off;
    put_byte(sector, &off, 0);
    put_byte(sector, &off, 0x58);                                 /* pop ax */
    put_byte(sector, &off, 0xba); put_word(sector, &off, 0x03f8); /* mov dx, 0x3f8 */
    put_byte(sector, &off, 0xee);                                 /* out dx, al */
    put_byte(sector, &off, 0xc3);                                 /* ret */

    size_t message_offset = off;
    put_text(sector, &off,
        "\r\n"
        "AuroraOS Pi Bring-Up Preview\r\n"
        "=============================\r\n"
        "\r\n"
        "[OK] Pixel UI: everything pixelated\r\n"
        "[OK] Assets: MSW98UI + click.wav\r\n"
        "[OK] systemd: Aurora session units\r\n"
        "[OK] Pi tools: GPIO I2C SPI UART fan\r\n"
        "[OK] Apps: native Flatpak AppImage\r\n"
        "[OK] Targets: Raspberry Pi 4 / Pi 5\r\n"
        "\r\n"
        "Next real milestone:\r\n"
        "Linux + systemd + Wayland + Aurora Shell.\r\n"
        "\r\n"
        "QEMU preview halted.\r\n");

    patch_word(sector, message_addr_patch, (uint16_t)(0x7c00 + message_offset));
    patch_rel16(sector, call_print_patch, print_loop);
    patch_rel16(sector, call_serial_patch, serial_putchar);
    patch_rel8(sector, jz_done_patch, print_done);
    patch_rel8(sector, jmp_print_patch, print_loop);
    patch_rel8(sector, serial_wait_patch, serial_wait);

    sector[510] = 0x55;
    sector[511] = 0xaa;

    FILE *out = fopen(argv[1], "wb");
    if (!out) {
        perror(argv[1]);
        return 1;
    }
    if (fwrite(sector, 1, sizeof(sector), out) != sizeof(sector)) {
        perror("fwrite");
        fclose(out);
        return 1;
    }
    fclose(out);
    return 0;
}
