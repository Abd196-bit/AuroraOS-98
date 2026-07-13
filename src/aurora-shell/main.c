#include <stdio.h>
#include "shell_contract.h"
#include "pixel_theme.h"

int main(void)
{
    puts("aurora-shell");
    printf("taskbar-height=%d\n", AURORA_TASKBAR_HEIGHT_PX);
    printf("titlebar-height=%d\n", AURORA_TITLEBAR_HEIGHT_PX);
    printf("desktop-color=#%06x\n", AURORA_COLOR_DESKTOP);
    puts("surfaces: desktop, taskbar, start menu, tray, notification center");
    puts("assets: MSW98UI fonts + click.wav through /usr/share/aurora/assets/manifest.json");
    puts("rule: every visible shell pixel is authored or scaled as pixel art");
    return 0;
}
