#ifndef AURORA_PIXEL_THEME_H
#define AURORA_PIXEL_THEME_H

#define AURORA_COLOR_GRAY        0xc0c0c0
#define AURORA_COLOR_WHITE       0xffffff
#define AURORA_COLOR_MID_GRAY    0x808080
#define AURORA_COLOR_DARK_GRAY   0x404040
#define AURORA_COLOR_BLACK       0x000000
#define AURORA_COLOR_TITLE_BLUE  0x0b168f
#define AURORA_COLOR_TITLE_CYAN  0x0078d4
#define AURORA_COLOR_DESKTOP     0x2f8f8a
#define AURORA_COLOR_SELECT      0x0b168f

struct aurora_bevel {
    unsigned int top_left;
    unsigned int face;
    unsigned int bottom_right_outer;
    unsigned int bottom_right_inner;
};

static const struct aurora_bevel AURORA_BEVEL_RAISED = {
    AURORA_COLOR_WHITE,
    AURORA_COLOR_GRAY,
    AURORA_COLOR_BLACK,
    AURORA_COLOR_MID_GRAY
};

static const struct aurora_bevel AURORA_BEVEL_PRESSED = {
    AURORA_COLOR_BLACK,
    AURORA_COLOR_GRAY,
    AURORA_COLOR_WHITE,
    AURORA_COLOR_MID_GRAY
};

#endif
