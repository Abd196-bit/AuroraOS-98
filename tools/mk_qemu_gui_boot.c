#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define COLS 80
#define ROWS 25
#define SCREEN_BYTES (COLS * ROWS * 2)
#define FRAME_SECTORS 8
#define FRAME_COUNT 5

enum vga_color {
    BLACK = 0,
    BLUE = 1,
    GREEN = 2,
    CYAN = 3,
    RED = 4,
    MAGENTA = 5,
    BROWN = 6,
    LIGHT_GRAY = 7,
    DARK_GRAY = 8,
    LIGHT_BLUE = 9,
    LIGHT_GREEN = 10,
    LIGHT_CYAN = 11,
    LIGHT_RED = 12,
    LIGHT_MAGENTA = 13,
    YELLOW = 14,
    WHITE = 15
};

static uint8_t attr(enum vga_color fg, enum vga_color bg)
{
    return (uint8_t)((bg << 4) | fg);
}

static void cell(uint8_t *screen, int x, int y, uint8_t ch, uint8_t a)
{
    if (x < 0 || y < 0 || x >= COLS || y >= ROWS) return;
    screen[(y * COLS + x) * 2] = ch;
    screen[(y * COLS + x) * 2 + 1] = a;
}

static void text(uint8_t *screen, int x, int y, const char *s, uint8_t a)
{
    for (int i = 0; s[i] != '\0'; i++) cell(screen, x + i, y, (uint8_t)s[i], a);
}

static void fill(uint8_t *screen, int x, int y, int w, int h, uint8_t ch, uint8_t a)
{
    for (int row = 0; row < h; row++) {
        for (int col = 0; col < w; col++) cell(screen, x + col, y + row, ch, a);
    }
}

static void border(uint8_t *screen, int x, int y, int w, int h, uint8_t a)
{
    for (int col = 0; col < w; col++) {
        cell(screen, x + col, y, '-', a);
        cell(screen, x + col, y + h - 1, '-', a);
    }
    for (int row = 0; row < h; row++) {
        cell(screen, x, y + row, '|', a);
        cell(screen, x + w - 1, y + row, '|', a);
    }
    cell(screen, x, y, '+', a);
    cell(screen, x + w - 1, y, '+', a);
    cell(screen, x, y + h - 1, '+', a);
    cell(screen, x + w - 1, y + h - 1, '+', a);
}

static void icon(uint8_t *screen, int x, int y, enum vga_color c, const char *label)
{
    uint8_t px = attr(c, BLACK);
    cell(screen, x, y, 219, px);
    cell(screen, x + 1, y, 219, px);
    cell(screen, x, y + 1, 219, px);
    cell(screen, x + 1, y + 1, 219, px);
    text(screen, x + 3, y, label, attr(BLACK, LIGHT_GRAY));
}

static void button(uint8_t *screen, int x, int y, int w, const char *label, int selected)
{
    uint8_t face = selected ? attr(WHITE, BLUE) : attr(BLACK, LIGHT_GRAY);
    uint8_t edge = selected ? attr(WHITE, BLUE) : attr(WHITE, LIGHT_GRAY);
    fill(screen, x, y, w, 3, ' ', face);
    border(screen, x, y, w, 3, edge);
    text(screen, x + 2, y + 1, label, face);
}

static void panel(uint8_t *screen, int x, int y, int w, int h, const char *title)
{
    fill(screen, x, y, w, h, ' ', attr(BLACK, LIGHT_GRAY));
    border(screen, x, y, w, h, attr(WHITE, LIGHT_GRAY));
    text(screen, x + 2, y + 1, title, attr(BLACK, LIGHT_GRAY));
}

static void chrome(uint8_t *screen, const char *active)
{
    uint8_t desktop = attr(BLACK, CYAN);
    uint8_t face = attr(BLACK, LIGHT_GRAY);
    uint8_t title = attr(WHITE, BLUE);

    fill(screen, 0, 0, COLS, ROWS, 177, desktop);
    fill(screen, 1, 1, 78, 23, ' ', face);
    border(screen, 1, 1, 78, 23, attr(WHITE, LIGHT_GRAY));
    fill(screen, 2, 2, 76, 1, ' ', title);
    text(screen, 4, 2, "AuroraOS Developer Preview", title);
    text(screen, 70, 2, "_ [] X", title);
    text(screen, 3, 4, "1 Start  2 Explorer  3 Packages  4 Pi Tools  5 Terminal  Q Quit", face);
    fill(screen, 2, 5, 76, 1, '-', attr(WHITE, LIGHT_GRAY));
    text(screen, 3, 22, "Keyboard: press 1-5 to switch apps. Everything is pixelated.", face);
    text(screen, 58, 22, active, attr(WHITE, BLUE));
}

static void draw_start(uint8_t *screen)
{
    chrome(screen, "Start");
    button(screen, 3, 6, 11, "Start", 1);
    panel(screen, 3, 10, 18, 11, "Start Menu");
    icon(screen, 5, 12, YELLOW, "Explorer");
    icon(screen, 5, 14, LIGHT_GREEN, "Package Center");
    icon(screen, 5, 16, LIGHT_CYAN, "Pi Tools");
    icon(screen, 5, 18, WHITE, "Terminal");
    panel(screen, 23, 8, 52, 13, "Aurora Desktop");
    text(screen, 26, 10, "Custom Linux OS shell for Raspberry Pi.", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 12, "[OK] original pixel icons generated", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 13, "[OK] MSW98UI fonts and click sound staged", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 14, "[OK] QEMU keyboard demo booted", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 16, "This is firmware-level GUI progress.", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 17, "Next: real Linux + Wayland Aurora Shell.", attr(BLACK, LIGHT_GRAY));
}

static void draw_explorer(uint8_t *screen)
{
    chrome(screen, "Explorer");
    button(screen, 14, 6, 13, "Explorer", 1);
    panel(screen, 3, 8, 18, 13, "Folders");
    text(screen, 5, 10, "> This Pi", attr(WHITE, BLUE));
    text(screen, 5, 11, "  Desktop", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 12, "  Documents", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 13, "  Apps", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 14, "  GPIO", attr(BLACK, LIGHT_GRAY));
    panel(screen, 23, 8, 52, 13, "Aurora Explorer");
    icon(screen, 26, 10, YELLOW, "Applications");
    icon(screen, 26, 12, WHITE, "Documents");
    icon(screen, 26, 14, LIGHT_GREEN, "Raspberry Pi Devices");
    icon(screen, 26, 16, LIGHT_CYAN, "System Disk");
}

static void draw_packages(uint8_t *screen)
{
    chrome(screen, "Packages");
    button(screen, 28, 6, 14, "Packages", 1);
    panel(screen, 3, 8, 18, 13, "Categories");
    text(screen, 5, 10, "> All Software", attr(WHITE, BLUE));
    text(screen, 5, 11, "  Updates", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 12, "  Installed", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 13, "  Flatpak", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 14, "  AppImage", attr(BLACK, LIGHT_GRAY));
    panel(screen, 23, 8, 52, 13, "Package Center");
    text(screen, 26, 10, "Name             Source      Status", attr(WHITE, BLUE));
    text(screen, 26, 12, "Chromium         Native      Installed", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 13, "VSCodium         Native      Installed", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 14, "Godot            Flatpak     Available", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 15, "Steam            Installer   Optional", attr(BLACK, LIGHT_GRAY));
}

static void draw_pi(uint8_t *screen)
{
    chrome(screen, "Pi Tools");
    button(screen, 43, 6, 11, "Pi", 1);
    panel(screen, 3, 8, 18, 13, "Pi Tools");
    text(screen, 5, 10, "> GPIO Manager", attr(WHITE, BLUE));
    text(screen, 5, 11, "  Camera Tools", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 12, "  UART Terminal", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 13, "  SPI Tools", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 14, "  I2C Tools", attr(BLACK, LIGHT_GRAY));
    text(screen, 5, 15, "  Fan Control", attr(BLACK, LIGHT_GRAY));
    panel(screen, 23, 8, 52, 13, "Raspberry Pi Monitor");
    text(screen, 26, 10, "CPU  [########------]  38%", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 12, "GPU  [#####---------]  22%", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 14, "RAM  [#########-----]  612 MB", attr(BLACK, LIGHT_GRAY));
    text(screen, 26, 16, "FAN  [########------]  55%", attr(BLACK, LIGHT_GRAY));
}

static void draw_terminal(uint8_t *screen)
{
    chrome(screen, "Terminal");
    button(screen, 55, 6, 13, "Terminal", 1);
    panel(screen, 3, 8, 72, 13, "Aurora Terminal");
    fill(screen, 5, 10, 68, 9, ' ', attr(LIGHT_GREEN, BLACK));
    text(screen, 6, 10, "AuroraOS 0.1 Pi shell demo", attr(LIGHT_GREEN, BLACK));
    text(screen, 6, 12, "display: QEMU VGA text mode", attr(LIGHT_GREEN, BLACK));
    text(screen, 6, 13, "target: Linux + systemd + Wayland + Aurora Shell", attr(LIGHT_GREEN, BLACK));
    text(screen, 6, 15, "aurora@pi:~$ press 1-5 to switch apps", attr(LIGHT_GREEN, BLACK));
}

static void put_byte(uint8_t *sector, size_t *offset, uint8_t value)
{
    if (*offset >= 510) {
        fprintf(stderr, "boot sector overflow\n");
        exit(1);
    }
    sector[(*offset)++] = value;
}

static void put_word(uint8_t *sector, size_t *offset, uint16_t value)
{
    put_byte(sector, offset, (uint8_t)(value & 0xff));
    put_byte(sector, offset, (uint8_t)(value >> 8));
}

static void patch_word(uint8_t *sector, size_t offset, uint16_t value)
{
    sector[offset] = (uint8_t)(value & 0xff);
    sector[offset + 1] = (uint8_t)(value >> 8);
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

static void patch_rel8(uint8_t *sector, size_t offset, size_t target)
{
    int rel = (int)target - (int)(offset + 1);
    if (rel < -128 || rel > 127) {
        fprintf(stderr, "rel8 out of range\n");
        exit(1);
    }
    sector[offset] = (uint8_t)rel;
}

static void make_boot_sector(uint8_t *sector)
{
    size_t off = 0;
    memset(sector, 0, 512);

    put_byte(sector, &off, 0xfa); /* cli */
    put_byte(sector, &off, 0x31); put_byte(sector, &off, 0xc0); /* xor ax, ax */
    put_byte(sector, &off, 0x8e); put_byte(sector, &off, 0xd8); /* mov ds, ax */
    put_byte(sector, &off, 0x8e); put_byte(sector, &off, 0xd0); /* mov ss, ax */
    put_byte(sector, &off, 0xbc); put_word(sector, &off, 0x7c00); /* mov sp, 7c00 */
    put_byte(sector, &off, 0x88); put_byte(sector, &off, 0x16);
    size_t boot_drive_patch = off; put_word(sector, &off, 0); /* mov [boot_drive], dl */
    put_byte(sector, &off, 0xfb); /* sti */
    put_byte(sector, &off, 0xb8); put_word(sector, &off, 0x0003); /* mov ax, 3 */
    put_byte(sector, &off, 0xcd); put_byte(sector, &off, 0x10); /* int 10 */
    put_byte(sector, &off, 0xb8); put_word(sector, &off, 1); /* mov ax, lba 1 */
    put_byte(sector, &off, 0xe8); size_t call_initial_patch = off; put_word(sector, &off, 0);

    size_t loop = off;
    put_byte(sector, &off, 0x30); put_byte(sector, &off, 0xe4); /* xor ah, ah */
    put_byte(sector, &off, 0xcd); put_byte(sector, &off, 0x16); /* int 16 */

    const char keys[] = {'1', '2', '3', '4', '5', 'q', 'Q'};
    size_t je_patches[7];
    for (size_t i = 0; i < sizeof(keys); i++) {
        put_byte(sector, &off, 0x3c); put_byte(sector, &off, (uint8_t)keys[i]); /* cmp al, key */
        put_byte(sector, &off, 0x74); je_patches[i] = off; put_byte(sector, &off, 0); /* je */
    }
    put_byte(sector, &off, 0xeb); size_t loop_jmp_patch = off; put_byte(sector, &off, 0);

    size_t key_labels[7];
    for (int i = 0; i < 5; i++) {
        key_labels[i] = off;
        put_byte(sector, &off, 0xb8); put_word(sector, &off, (uint16_t)(1 + i * FRAME_SECTORS));
        put_byte(sector, &off, 0xe8); size_t call_read_patch = off; put_word(sector, &off, 0);
        put_byte(sector, &off, 0xeb); size_t key_loop_patch = off; put_byte(sector, &off, 0);
        je_patches[5] = je_patches[5];
        patch_rel16(sector, call_read_patch, 0); /* temporary marker */
        sector[call_read_patch] = 0xfe;
        sector[call_read_patch + 1] = 0xff;
        sector[key_loop_patch] = 0xfe;
    }

    key_labels[5] = off;
    key_labels[6] = off;
    put_byte(sector, &off, 0xf4); /* hlt */
    put_byte(sector, &off, 0xeb); put_byte(sector, &off, 0xfd);

    size_t read_frame = off;
    put_byte(sector, &off, 0xa3); size_t dap_lba_patch = off; put_word(sector, &off, 0); /* mov [dap_lba], ax */
    put_byte(sector, &off, 0x31); put_byte(sector, &off, 0xc0); /* xor ax, ax */
    put_byte(sector, &off, 0xa3); size_t dap_lba2_patch = off; put_word(sector, &off, 0);
    put_byte(sector, &off, 0xa3); size_t dap_lba4_patch = off; put_word(sector, &off, 0);
    put_byte(sector, &off, 0xa3); size_t dap_lba6_patch = off; put_word(sector, &off, 0);
    put_byte(sector, &off, 0xbe); size_t dap_patch = off; put_word(sector, &off, 0); /* mov si, dap */
    put_byte(sector, &off, 0x8a); put_byte(sector, &off, 0x16); size_t drive_ref_patch = off; put_word(sector, &off, 0);
    put_byte(sector, &off, 0xb4); put_byte(sector, &off, 0x42); /* mov ah, 42 */
    put_byte(sector, &off, 0xcd); put_byte(sector, &off, 0x13); /* int 13 */
    put_byte(sector, &off, 0xc3); /* ret */

    size_t boot_drive = off;
    put_byte(sector, &off, 0);
    size_t dap = off;
    put_byte(sector, &off, 0x10); put_byte(sector, &off, 0x00);
    put_word(sector, &off, FRAME_SECTORS);
    put_word(sector, &off, 0x0000);
    put_word(sector, &off, 0xb800);
    size_t dap_lba = off;
    put_word(sector, &off, 0x0001);
    put_word(sector, &off, 0x0000);
    put_word(sector, &off, 0x0000);
    put_word(sector, &off, 0x0000);

    patch_word(sector, boot_drive_patch, (uint16_t)(0x7c00 + boot_drive));
    patch_rel16(sector, call_initial_patch, read_frame);
    patch_rel8(sector, loop_jmp_patch, loop);
    for (int i = 0; i < 7; i++) patch_rel8(sector, je_patches[i], key_labels[i]);

    for (size_t i = 0; i + 1 < off; i++) {
        if (sector[i] == 0xfe && sector[i + 1] == 0xff) {
            patch_rel16(sector, i, read_frame);
        } else if (sector[i] == 0xfe) {
            patch_rel8(sector, i, loop);
        }
    }

    patch_word(sector, dap_lba_patch, (uint16_t)(0x7c00 + dap_lba));
    patch_word(sector, dap_lba2_patch, (uint16_t)(0x7c00 + dap_lba + 2));
    patch_word(sector, dap_lba4_patch, (uint16_t)(0x7c00 + dap_lba + 4));
    patch_word(sector, dap_lba6_patch, (uint16_t)(0x7c00 + dap_lba + 6));
    patch_word(sector, dap_patch, (uint16_t)(0x7c00 + dap));
    patch_word(sector, drive_ref_patch, (uint16_t)(0x7c00 + boot_drive));

    sector[510] = 0x55;
    sector[511] = 0xaa;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s OUTPUT.img\n", argv[0]);
        return 1;
    }

    uint8_t boot[512];
    uint8_t frames[FRAME_COUNT][FRAME_SECTORS * 512];
    memset(frames, 0, sizeof(frames));

    draw_start(frames[0]);
    draw_explorer(frames[1]);
    draw_packages(frames[2]);
    draw_pi(frames[3]);
    draw_terminal(frames[4]);
    make_boot_sector(boot);

    FILE *out = fopen(argv[1], "wb");
    if (!out) {
        perror(argv[1]);
        return 1;
    }
    fwrite(boot, 1, sizeof(boot), out);
    fwrite(frames, 1, sizeof(frames), out);
    fclose(out);
    return 0;
}
