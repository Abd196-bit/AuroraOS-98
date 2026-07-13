#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <sys/wait.h>
#include <signal.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <sys/types.h>

#define FB_W 1280
#define FB_H 800
#define PIXEL_BYTES 4
#define FRAME_BYTES (FB_W * FB_H * PIXEL_BYTES)
#define FRAME_OPEN_BASE 2
#define FRAME_SUBMENU_BASE 10
#define FRAME_TAB_BASE 16
#define FRAME_DIALOG_BASE 20
#define START_ITEMS 8
#define SUBMENU_ITEMS 6
#define DIALOG_COUNT 17
#define FRAME_COUNT 37
#define NET_CHECK_INTERVAL 5  /* Cache network status for 5 seconds */

enum screen_id {
    SCREEN_CLOSED = 0,
    SCREEN_STATUS = 1,
};

enum dialog_id {
    DIALOG_PACKAGE = 0,
    DIALOG_DOCUMENTS,
    DIALOG_SETTINGS,
    DIALOG_FIND,
    DIALOG_HELP,
    DIALOG_RUN,
    DIALOG_SUSPEND,
    DIALOG_SHUTDOWN,
    DIALOG_TERMINAL,
    DIALOG_EXPLORER,
    DIALOG_CONTROL,
    DIALOG_DRIVE,
    DIALOG_NETWORK,
    DIALOG_RECYCLE,
    DIALOG_ABOUT,
    DIALOG_BROWSER,
    DIALOG_FEATURES,
};

static const char *frame_paths[FRAME_COUNT] = {
    "/aurora/desktop-closed.bgra32",
    "/aurora/status.bgra32",
    "/aurora/desktop-open-0.bgra32",
    "/aurora/desktop-open-1.bgra32",
    "/aurora/desktop-open-2.bgra32",
    "/aurora/desktop-open-3.bgra32",
    "/aurora/desktop-open-4.bgra32",
    "/aurora/desktop-open-5.bgra32",
    "/aurora/desktop-open-6.bgra32",
    "/aurora/desktop-open-7.bgra32",
    "/aurora/desktop-submenu-0.bgra32",
    "/aurora/desktop-submenu-1.bgra32",
    "/aurora/desktop-submenu-2.bgra32",
    "/aurora/desktop-submenu-3.bgra32",
    "/aurora/desktop-submenu-4.bgra32",
    "/aurora/desktop-submenu-5.bgra32",
    "/aurora/system-tab-0.bgra32",
    "/aurora/system-tab-1.bgra32",
    "/aurora/system-tab-2.bgra32",
    "/aurora/system-tab-3.bgra32",
    "/aurora/dialog-package.bgra32",
    "/aurora/dialog-documents.bgra32",
    "/aurora/dialog-settings.bgra32",
    "/aurora/dialog-find.bgra32",
    "/aurora/dialog-help.bgra32",
    "/aurora/dialog-run.bgra32",
    "/aurora/dialog-suspend.bgra32",
    "/aurora/dialog-shutdown.bgra32",
    "/aurora/dialog-terminal.bgra32",
    "/aurora/dialog-explorer.bgra32",
    "/aurora/dialog-control.bgra32",
    "/aurora/dialog-drive.bgra32",
    "/aurora/dialog-network.bgra32",
    "/aurora/dialog-recycle.bgra32",
    "/aurora/dialog-about.bgra32",
    "/aurora/dialog-browser.bgra32",
    "/aurora/dialog-features.bgra32",
};

static uint8_t *frames[FRAME_COUNT];
static uint8_t *work;
static int fb_fd = -1;
static int screen = FRAME_SUBMENU_BASE;
static int mouse_x = 328;
static int mouse_y = 365;
static int start_open = 1;
static int menu_selected = 0;
static int submenu_selected = 0;
static int submenu_active = 1;
static int esc_state = 0;
static int active_tab = 0;

/* Optimization: network status caching */
static int cached_network_status = -1;
static time_t last_network_check = 0;

/* Startup complete flag */
static volatile int startup_complete = 0;

static void die(const char *msg) {
    perror(msg);
    _exit(1);
}

/* Signal handlers for proper cleanup */
static void sigchld_handler(int sig) {
    (void)sig;
    /* Reap all dead children to prevent zombies */
    while (waitpid(-1, NULL, WNOHANG) > 0);
}

static void sigterm_handler(int sig) {
    (void)sig;
    /* Graceful exit on SIGTERM */
    if (fb_fd >= 0) close(fb_fd);
    _exit(0);
}

/* Network and system integration functions */

static int get_network_status_cached(void) {
    /* Check if cached result is still valid */
    time_t now = time(NULL);
    if (cached_network_status >= 0 && (now - last_network_check) < NET_CHECK_INTERVAL) {
        return cached_network_status;
    }
    
    /* Perform fresh network check */
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        cached_network_status = 0;
        last_network_check = now;
        return 0;
    }
    
    /* Set non-blocking socket with timeout */
    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);
    
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(53);
    inet_aton("8.8.8.8", &addr.sin_addr);
    
    int connected = (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0 || 
                    errno == EINPROGRESS);
    close(sock);
    
    cached_network_status = connected ? 1 : 0;
    last_network_check = now;
    return cached_network_status;
}

static int is_internet_connected(void) {
    return get_network_status_cached();
}

static void launch_program(const char *program, const char *arg1, const char *arg2) {
    pid_t pid = fork();
    if (pid == 0) {
        /* Child process: detach and launch */
        pid_t grandchild = fork();
        if (grandchild == 0) {
            /* Grandchild: actual program launch */
            setsid();
            int devnull = open("/dev/null", O_WRONLY);
            if (devnull >= 0) {
                dup2(devnull, STDOUT_FILENO);
                dup2(devnull, STDERR_FILENO);
                close(devnull);
            }
            if (arg2) {
                execl("/bin/sh", "sh", "-c", program, arg1, arg2, (char*)NULL);
            } else if (arg1) {
                execl("/bin/sh", "sh", "-c", program, arg1, (char*)NULL);
            } else {
                execl("/bin/sh", "sh", "-c", program, (char*)NULL);
            }
            _exit(127);
        }
        _exit(0);  /* Parent of grandchild exits */
    } else if (pid > 0) {
        /* Parent: wait for intermediate process to exit */
        waitpid(pid, NULL, 0);
    }
}

static void launch_browser(void) {
    const char *cmd = "if command -v chromium >/dev/null 2>&1; then exec chromium; "
                      "elif command -v chromium-browser >/dev/null 2>&1; then exec chromium-browser; "
                      "elif command -v x-www-browser >/dev/null 2>&1; then exec x-www-browser; "
                      "else exit 127; fi </dev/null >/dev/null 2>&1 &";
    launch_program(cmd, NULL, NULL);
    fprintf(stderr, "aurora-shell: launching web browser...\n");
}

static void launch_terminal(void) {
    const char *cmd = "if command -v aurora-terminal >/dev/null 2>&1; then exec aurora-terminal; "
                      "elif command -v xterm >/dev/null 2>&1; then exec xterm -bg black -fg '#55ff55'; "
                      "elif command -v foot >/dev/null 2>&1; then exec foot; "
                      "else exit 127; fi </dev/null >/dev/null 2>&1 &";
    launch_program(cmd, NULL, NULL);
    fprintf(stderr, "aurora-shell: launching terminal...\n");
}

static void launch_file_manager(void) {
    const char *cmd = "if command -v aurora-explorer >/dev/null 2>&1; then exec aurora-explorer; "
                      "elif command -v pcmanfm >/dev/null 2>&1; then exec pcmanfm ~; "
                      "elif command -v thunar >/dev/null 2>&1; then exec thunar ~; "
                      "else exit 127; fi </dev/null >/dev/null 2>&1 &";
    launch_program(cmd, NULL, NULL);
    fprintf(stderr, "aurora-shell: launching file manager...\n");
}

static void launch_package_center(void) {
    const char *cmd = "if command -v aurora-package-center >/dev/null 2>&1; then exec aurora-package-center; "
                      "elif command -v plasma-discover >/dev/null 2>&1; then exec plasma-discover; "
                      "elif command -v gnome-software >/dev/null 2>&1; then exec gnome-software; "
                      "else exit 127; fi </dev/null >/dev/null 2>&1 &";
    launch_program(cmd, NULL, NULL);
    fprintf(stderr, "aurora-shell: launching package center...\n");
}

static void show_network_status(void) {
    int connected = is_internet_connected();
    if (connected) {
        fprintf(stderr, "aurora-shell: Network Status: CONNECTED ✓\n");
    } else {
        fprintf(stderr, "aurora-shell: Network Status: DISCONNECTED\n");
    }
    fflush(stderr);
}

static void read_exact_file(const char *path, uint8_t *dst, size_t size) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "aurora-shell: ERROR opening %s: %s\n", path, strerror(errno));
        fprintf(stderr, "aurora-shell: VERIFY: /aurora directory exists with all .bgra32 files\n");
        fprintf(stderr, "aurora-shell: VERIFY: Running from initramfs with proper filesystem layout\n");
        die(path);
    }
    
    /* Set read timeout using alarm */
    alarm(3);
    
    size_t off = 0;
    while (off < size) {
        ssize_t n = read(fd, dst + off, size - off);
        if (n < 0) {
            if (errno == EINTR) continue;
            fprintf(stderr, "aurora-shell: read error from %s: %s\n", path, strerror(errno));
            die("read frame");
        }
        if (n == 0) {
            fprintf(stderr, "aurora-shell: short read from %s (%zu/%zu bytes)\n", path, off, size);
            alarm(0);
            close(fd);
            _exit(1);
        }
        off += (size_t)n;
    }
    
    alarm(0);
    close(fd);
}

static void put_px(int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x < 0 || y < 0 || x >= FB_W || y >= FB_H) {
        return;
    }
    size_t off = ((size_t)y * FB_W + (size_t)x) * PIXEL_BYTES;
    work[off + 0] = b;
    work[off + 1] = g;
    work[off + 2] = r;
    work[off + 3] = 0;
}

static int point_in_cursor(int x, int y) {
    if (x < 0 || y < 0 || x > 24 || y > 31) {
        return 0;
    }
    if (x <= 2 && y <= 25) {
        return 1;
    }
    if (y >= x && y <= x + 16 && x <= 18) {
        return 1;
    }
    if (x >= 7 && x <= 14 && y >= 18 && y <= 30) {
        return 1;
    }
    if (x >= 10 && x <= 20 && y >= 17 && y <= 21) {
        return 1;
    }
    return 0;
}

static int point_on_cursor_edge(int x, int y) {
    if (!point_in_cursor(x, y)) {
        return 0;
    }
    return !point_in_cursor(x - 1, y) || !point_in_cursor(x + 1, y) ||
           !point_in_cursor(x, y - 1) || !point_in_cursor(x, y + 1);
}

static void draw_cursor(void) {
    for (int y = -1; y < 33; y++) {
        for (int x = -1; x < 26; x++) {
            int lx = x;
            int ly = y;
            if (point_on_cursor_edge(lx, ly)) {
                put_px(mouse_x + x, mouse_y + y, 0, 0, 0);
            } else if (point_in_cursor(lx, ly)) {
                put_px(mouse_x + x, mouse_y + y, 255, 255, 255);
            }
        }
    }
}

static void repaint(void) {
    if (fb_fd < 0) return;
    
    memcpy(work, frames[screen], FRAME_BYTES);
    draw_cursor();
    
    /* Optimized framebuffer write with larger buffer */
    ssize_t written = 0;
    if (lseek(fb_fd, 0, SEEK_SET) == 0) {
        while (written < FRAME_BYTES) {
            ssize_t n = write(fb_fd, work + written, FRAME_BYTES - (size_t)written);
            if (n <= 0) {
                if (errno == EINTR) continue;
                if (errno != EIO) perror("repaint: write");
                break;
            }
            written += n;
        }
    }
}

static void set_screen(int next) {
    screen = next;
    start_open = (next >= FRAME_OPEN_BASE);
    repaint();
}

static int base_x(void) {
    int x = ((mouse_x - 107) * 640) / 1066;
    if (x < 0) return -1;
    if (x > 639) return 640;
    return x;
}

static int base_y(void) {
    int y = (mouse_y * 480) / 800;
    if (y < 0) return -1;
    if (y > 479) return 480;
    return y;
}

static void show_closed(void) {
    submenu_active = 0;
    set_screen(SCREEN_CLOSED);
}

static void show_menu(void) {
    start_open = 1;
    if (menu_selected == 0 && submenu_active) {
        set_screen(FRAME_SUBMENU_BASE + submenu_selected);
    } else {
        submenu_active = 0;
        set_screen(FRAME_OPEN_BASE + menu_selected);
    }
}

static void show_status(void) {
    submenu_active = 0;
    set_screen(SCREEN_STATUS);
}

static int is_dialog_screen(void) {
    return screen >= FRAME_DIALOG_BASE && screen < FRAME_DIALOG_BASE + DIALOG_COUNT;
}

static void show_tab(int tab) {
    if (tab < 0) tab = 0;
    if (tab > 3) tab = 3;
    active_tab = tab;
    submenu_active = 0;
    set_screen(FRAME_TAB_BASE + active_tab);
}

static void show_dialog(int dialog) {
    if (dialog < 0) dialog = DIALOG_HELP;
    if (dialog >= DIALOG_COUNT) dialog = DIALOG_HELP;
    submenu_active = 0;
    set_screen(FRAME_DIALOG_BASE + dialog);
}

static void close_popup(void) {
    show_closed();
}

static void activate_start_item(void) {
    if (menu_selected == 0) {
        submenu_active = 1;
        set_screen(FRAME_SUBMENU_BASE + submenu_selected);
        return;
    }
    switch (menu_selected) {
    case 1:
        show_network_status();
        show_dialog(DIALOG_NETWORK);
        break;
    case 2:
        show_dialog(DIALOG_SETTINGS);
        break;
    case 3:
        show_dialog(DIALOG_FIND);
        break;
    case 4:
        show_dialog(DIALOG_HELP);
        break;
    case 5:
        show_dialog(DIALOG_RUN);
        break;
    case 6:
        show_dialog(DIALOG_SUSPEND);
        break;
    case 7:
        show_dialog(DIALOG_SHUTDOWN);
        break;
    default:
        show_dialog(DIALOG_HELP);
        break;
    }
}

static void activate_submenu_item(void) {
    switch (submenu_selected) {
    case 0:
        show_dialog(DIALOG_ABOUT);
        break;
    case 1:
        show_dialog(DIALOG_CONTROL);
        break;
    case 2:
        show_dialog(DIALOG_DOCUMENTS);
        break;
    case 3:
        show_dialog(DIALOG_BROWSER);
        break;
    case 4:
        show_dialog(DIALOG_TERMINAL);
        break;
    case 5:
        show_dialog(DIALOG_PACKAGE);
        break;
    default:
        show_dialog(DIALOG_HELP);
        break;
    }
}

static void move_menu(int delta) {
    if (!start_open) {
        menu_selected = 0;
        submenu_selected = 0;
        submenu_active = 1;
        show_menu();
        return;
    }
    if (submenu_active) {
        submenu_selected = (submenu_selected + delta + SUBMENU_ITEMS) % SUBMENU_ITEMS;
    } else {
        menu_selected = (menu_selected + delta + START_ITEMS) % START_ITEMS;
        if (menu_selected == 0) {
            submenu_active = 1;
        }
    }
    show_menu();
}

static void move_right(void) {
    if (!start_open) {
        show_menu();
    } else if (menu_selected == 0) {
        submenu_active = 1;
        show_menu();
    }
}

static void move_left(void) {
    if (submenu_active) {
        submenu_active = 0;
        show_menu();
    }
}

static int inside(int x, int y, int x0, int y0, int x1, int y1) {
    return x >= x0 && x <= x1 && y >= y0 && y <= y1;
}

static void handle_click(void) {
    int x = base_x();
    int y = base_y();
    if (inside(x, y, 2, 454, 52, 476)) {
        if (start_open) {
            show_closed();
        } else {
            menu_selected = 0;
            submenu_selected = 0;
            submenu_active = 1;
            show_menu();
        }
        return;
    }
    if (is_dialog_screen()) {
        if (inside(x, y, 480, 120, 520, 146) || inside(x, y, 454, 292, 498, 324) ||
            inside(x, y, 302, 294, 500, 330)) {
            if (screen == FRAME_DIALOG_BASE + DIALOG_SHUTDOWN && inside(x, y, 318, 292, 404, 330)) {
                sync();
                _exit(0);
            }
            close_popup();
        }
        return;
    }
    if (screen == SCREEN_STATUS) {
        if (inside(x, y, 392, 294, 474, 318) || inside(x, y, 478, 404, 554, 426) ||
            inside(x, y, 564, 404, 632, 426) || inside(x, y, 611, 9, 628, 26)) {
            close_popup();
        }
        return;
    }
    if (inside(x, y, 24, 8, 96, 72)) {
        show_dialog(DIALOG_ABOUT);
        return;
    }
    if (inside(x, y, 24, 88, 116, 166)) {
        show_dialog(DIALOG_NETWORK);
        return;
    }
    if (inside(x, y, 24, 182, 104, 246)) {
        show_dialog(DIALOG_RECYCLE);
        return;
    }
    if (inside(x, y, 611, 9, 628, 26) || inside(x, y, 305, 57, 321, 73)) {
        close_popup();
        return;
    }
    if (inside(x, y, 240, 36, 290, 60)) {
        show_tab(0);
        return;
    }
    if (inside(x, y, 292, 36, 380, 60)) {
        show_tab(1);
        return;
    }
    if (inside(x, y, 382, 36, 510, 60)) {
        show_tab(2);
        return;
    }
    if (inside(x, y, 512, 36, 620, 60)) {
        show_tab(3);
        return;
    }
    if (inside(x, y, 478, 404, 554, 426) || inside(x, y, 564, 404, 632, 426)) {
        close_popup();
        return;
    }
    if (inside(x, y, 82, 96, 146, 150) || inside(x, y, 168, 96, 224, 150) ||
        inside(x, y, 236, 92, 314, 158)) {
        show_dialog(DIALOG_DRIVE);
        return;
    }
    if (inside(x, y, 84, 164, 158, 232)) {
        show_dialog(DIALOG_CONTROL);
        return;
    }
    if (inside(x, y, 162, 164, 240, 232)) {
        show_dialog(DIALOG_SETTINGS);
        return;
    }
    if (!start_open) {
        return;
    }
    if (inside(x, y, 30, 198, 158, 446)) {
        int idx = (y - 198) / 36;
        if (idx < 0) idx = 0;
        if (idx >= START_ITEMS) idx = START_ITEMS - 1;
        menu_selected = idx;
        submenu_active = (menu_selected == 0);
        show_menu();
        activate_start_item();
        return;
    }
    if (menu_selected == 0 && inside(x, y, 164, 186, 304, 300)) {
        int idx = (y - 196) / 22;
        if (idx < 0) idx = 0;
        if (idx >= SUBMENU_ITEMS) idx = SUBMENU_ITEMS - 1;
        submenu_selected = idx;
        submenu_active = 1;
        show_menu();
        activate_submenu_item();
        return;
    }
}

static void handle_command(char key) {
    switch (key) {
    case '1':
    case '2':
        show_closed();
        break;
    case '3':
        menu_selected = 0;
        submenu_selected = 0;
        submenu_active = 1;
        show_menu();
        break;
    case 's':
    case 'S':
        show_status();
        break;
    case 'g':
    case 'G':
        show_dialog(DIALOG_SETTINGS);
        break;
    case 'b':
    case 'B':
        show_dialog(DIALOG_BROWSER);
        break;
    case 'p':
    case 'P':
        show_dialog(DIALOG_PACKAGE);
        break;
    case 'd':
    case 'D':
        show_dialog(DIALOG_EXPLORER);
        break;
    case 'f':
    case 'F':
        show_dialog(DIALOG_FEATURES);
        break;
    case 'h':
    case 'H':
        show_dialog(DIALOG_HELP);
        break;
    case 'r':
    case 'R':
        show_dialog(DIALOG_RUN);
        break;
    case 't':
    case 'T':
        show_dialog(DIALOG_TERMINAL);
        break;
    case 'e':
    case 'E':
        show_dialog(DIALOG_EXPLORER);
        break;
    case 'c':
    case 'C':
        show_dialog(DIALOG_CONTROL);
        break;
    case 'a':
    case 'A':
        show_dialog(DIALOG_ABOUT);
        break;
    case 'n':
    case 'N':
        show_network_status();  /* N = Network status */
        break;
    case '\r':
    case '\n':
    case ' ':
        if (screen == SCREEN_STATUS || is_dialog_screen()) {
            if (screen == FRAME_DIALOG_BASE + DIALOG_SHUTDOWN) {
                sync();
                _exit(0);
            }
            close_popup();
        } else if (!start_open) {
            menu_selected = 0;
            submenu_selected = 0;
            submenu_active = 1;
            show_menu();
        } else if (submenu_active) {
            activate_submenu_item();
        } else {
            activate_start_item();
        }
        break;
    case 27:
        if (screen == SCREEN_STATUS || is_dialog_screen() || start_open) {
            close_popup();
        }
        break;
    case '\t':
        if (screen == SCREEN_STATUS || is_dialog_screen()) {
            close_popup();
        } else {
            start_open ? show_closed() : show_menu();
        }
        break;
    case '0':
        show_tab(0);
        break;
    case '4':
        show_tab(1);
        break;
    case '5':
        show_tab(2);
        break;
    case '6':
        show_tab(3);
        break;
    case 'q':
    case 'Q':
        sync();
        _exit(0);
    default:
        break;
    }
}

static void handle_key(char key) {
    if (esc_state == 0) {
        if (key == 27) {
            esc_state = 1;
            return;
        }
        handle_command(key);
        return;
    }
    if (esc_state == 1) {
        if (key == '[') {
            esc_state = 2;
            return;
        }
        esc_state = 0;
        handle_command(27);
        return;
    }
    esc_state = 0;
    switch (key) {
    case 'A':
        move_menu(-1);
        break;
    case 'B':
        move_menu(1);
        break;
    case 'C':
        move_right();
        break;
    case 'D':
        move_left();
        break;
    default:
        break;
    }
}

static int open_optional(const char *path, int flags) {
    int fd = open(path, flags);
    if (fd < 0) {
        fprintf(stderr, "aurora-shell: warning: cannot open %s: %s\n", path, strerror(errno));
    }
    return fd;
}

int main(void) {
    /* Setup signal handlers */
    signal(SIGCHLD, sigchld_handler);
    signal(SIGTERM, sigterm_handler);
    signal(SIGINT, sigterm_handler);
    
    /* Startup message */
    fprintf(stderr, "aurora-shell: starting AuroraOS shell\n");
    
    /* Allocate frame buffers */
    for (int i = 0; i < FRAME_COUNT; i++) {
        frames[i] = malloc(FRAME_BYTES);
        if (!frames[i]) die("malloc frames");
    }
    
    work = malloc(FRAME_BYTES);
    if (!work) die("malloc work buffer");
    
    fprintf(stderr, "aurora-shell: loading %d frames...\n", FRAME_COUNT);
    
    /* Load all frame assets */
    for (int i = 0; i < FRAME_COUNT; i++) {
        read_exact_file(frame_paths[i], frames[i], FRAME_BYTES);
        if (i % 5 == 0) {
            fprintf(stderr, "  %d/%d frames loaded\n", i + 1, FRAME_COUNT);
        }
    }
    
    fprintf(stderr, "aurora-shell: opening framebuffer device /dev/fb0\n");
    
    /* Open framebuffer */
    fb_fd = open("/dev/fb0", O_RDWR);
    if (fb_fd < 0) {
        fprintf(stderr, "aurora-shell: ERROR: cannot open /dev/fb0: %s\n", strerror(errno));
        fprintf(stderr, "aurora-shell: CHECK: ls -la /dev/fb* in initramfs\n");
        fprintf(stderr, "aurora-shell: CHECK: QEMU graphics enabled with -vga std\n");
        fprintf(stderr, "aurora-shell: CHECK: Framebuffer drivers loaded (bochs/cirrus/virtio-gpu)\n");
        die("/dev/fb0");
    }
    
    /* Setup keyboard */
    int tty_fd = open_optional("/dev/console", O_RDONLY | O_NONBLOCK);
    if (tty_fd >= 0) {
        struct termios tio;
        if (tcgetattr(tty_fd, &tio) == 0) {
            cfmakeraw(&tio);
            tio.c_lflag &= (tcflag_t)~ECHO;
            tcsetattr(tty_fd, TCSANOW, &tio);
            fprintf(stderr, "aurora-shell: keyboard initialized\n");
        }
    }
    
    /* Setup mouse */
    int mouse_fd = open_optional("/dev/input/mice", O_RDONLY | O_NONBLOCK);
    if (mouse_fd < 0) {
        mouse_fd = open_optional("/dev/input/mouse0", O_RDONLY | O_NONBLOCK);
    }
    if (mouse_fd >= 0) {
        fprintf(stderr, "aurora-shell: mouse initialized\n");
    }
    
    /* Check network status */
    fprintf(stderr, "aurora-shell: checking network connectivity...\n");
    if (is_internet_connected()) {
        fprintf(stderr, "aurora-shell: network CONNECTED\n");
    } else {
        fprintf(stderr, "aurora-shell: network DISCONNECTED\n");
    }
    
    fprintf(stderr, "aurora-shell: initialization complete\n");
    
    /* Initial render */
    repaint();
    startup_complete = 1;
    
    /* Main event loop */
    for (;;) {
        struct pollfd pfds[2];
        int nfds = 0;
        
        if (tty_fd >= 0) {
            pfds[nfds].fd = tty_fd;
            pfds[nfds].events = POLLIN;
            nfds++;
        }
        if (mouse_fd >= 0) {
            pfds[nfds].fd = mouse_fd;
            pfds[nfds].events = POLLIN;
            nfds++;
        }
        
        /* Poll with short timeout for responsiveness */
        int rc = poll(pfds, (nfds_t)nfds, 100);
        if (rc < 0) {
            if (errno == EINTR) continue;
            die("poll");
        }
        
        if (rc == 0) {
            /* Timeout: handle pending ESC state */
            if (esc_state) {
                esc_state = 0;
                handle_command(27);
            }
            continue;
        }
        
        /* Process keyboard input */
        int idx = 0;
        if (tty_fd >= 0) {
            if (pfds[idx].revents & POLLIN) {
                char key;
                while (read(tty_fd, &key, 1) == 1) {
                    handle_key(key);
                }
            }
            idx++;
        }
        
        /* Process mouse input */
        if (mouse_fd >= 0 && idx < nfds && (pfds[idx].revents & POLLIN)) {
            unsigned char packet[3];
            while (read(mouse_fd, packet, sizeof(packet)) == (ssize_t)sizeof(packet)) {
                int left = packet[0] & 1;
                int dx = (int)(int8_t)packet[1];
                int dy = (int)(int8_t)packet[2];
                mouse_x += dx * 2;
                mouse_y -= dy * 2;
                if (mouse_x < 0) mouse_x = 0;
                if (mouse_y < 0) mouse_y = 0;
                if (mouse_x > FB_W - 2) mouse_x = FB_W - 2;
                if (mouse_y > FB_H - 2) mouse_y = FB_H - 2;
                if (left) {
                    handle_click();
                } else {
                    repaint();
                }
            }
        }
    }
}
