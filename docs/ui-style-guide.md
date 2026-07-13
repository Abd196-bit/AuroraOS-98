# AuroraOS Pixel UI Style Guide

This guide follows the supplied reference image: dense gray UI, beveled controls, blue title bars, square panels, black outlines, and pixelated typography.

## Non-Negotiable Rule

Everything visible must be pixelated.

No exceptions for:

- icons
- cursors
- title bars
- window borders
- wallpapers
- loading indicators
- installer graphics
- login screen
- settings panels
- package cards

## Rendering Rules

- Use the supplied MSW98UI font files for shell UI.
- Use the user-provided icon pack converted into `assets/icons/system/` for this prototype.
- Before public distribution, replace Microsoft-derived compatibility icons with original Aurora artwork.
- Render shell fonts with crisp pixel settings where toolkit support allows it.
- Use nearest-neighbor scaling for all bitmap UI assets.
- Scale only by integer factors: 1x, 2x, 3x, 4x.
- Use a fixed pixel grid for all shell controls.
- Icons are authored as pixel art at canonical sizes: 16, 24, 32, and 48 px.
- Do not use SVG icons for visible shell chrome unless they are rasterized into pixel assets at build time.

## Window Rules

- corners are always square
- title bar height is fixed per scale tier
- active title bar uses a saturated blue Aurora gradient or solid blue band
- inactive title bar uses gray
- window body uses classic gray
- borders use 3D bevels: highlight top/left, shadow bottom/right
- resize grips are pixelated
- close/minimize/maximize buttons are beveled square buttons

## Bevel System

Raised control:

```text
top/left:    #ffffff
middle:      #c0c0c0
bottom/right:#000000 then #808080
```

Pressed control:

```text
top/left:    #000000 then #808080
middle:      #b8b8b8
bottom/right:#ffffff
```

Focus ring:

```text
1 px dotted black rectangle inside the control
```

## Layout Rules

- dense spacing
- keyboard and mouse first
- no mobile-first oversized padding
- all controls align to the pixel grid
- panels use square borders
- menus use compact rows
- status bars are visible and useful
- no card-heavy modern dashboards

## Wallpaper

Default wallpaper should use original Aurora pixel artwork. A good first direction is a teal geometric repeating pattern like the reference image, but not copied from any Microsoft asset.

Requirements:

- tileable
- pixel authored
- not blurred
- not gradient-orb based
- works at integer scale

## Color Base

```text
aurora-gray:        #c0c0c0
aurora-gray-light:  #ffffff
aurora-gray-mid:    #808080
aurora-gray-dark:   #404040
aurora-black:       #000000
aurora-title-blue:  #0b168f
aurora-title-cyan:  #0078d4
aurora-desktop:     #2f8f8a
aurora-select:      #0b168f
aurora-select-text: #ffffff
```

## Application Chrome

Aurora-owned apps must use the same shell chrome:

- Explorer
- Package Center
- Settings
- Control Panel
- Terminal
- Task Manager
- Disk Manager
- Pi Tools

Third-party Linux apps should not be forcibly reskinned. They run as compatible apps inside Aurora-managed windows.

## Sound Rules

Use `click.wav` for:

- button activation
- menu activation
- taskbar activation
- dialog confirmation

Do not play sounds for high-frequency events like mouse hover, drag, resize, or text entry.
