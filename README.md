# DotDotGoose (Fork)

> **This is a modified fork** of [DotDotGoose](https://github.com/persts/DotDotGoose) by Peter Ersts (AMNH).  
> Licensed under [GPLv3](LICENSE). All original copyright and attribution are preserved.

DotDotGoose is a free, open source tool to assist with manually counting objects in images.

![Screen Shot](doc/source/example.png)

*Point data collected with DotDotGoose will be very valuable training and validation data for any future efforts with computer assisted counting*

## Fork Changes (v1.7.0-fork.3)

- **Cross-image undo/redo** — global undo stack with image navigation; supports add, delete, move, relabel, rename class, add/remove class, and color change operations. Redo via `Ctrl+Shift+Z`.
- **Selection & interaction** — rubber-band multi-select, drag-move points, right-click mode toggle (add ↔ select/move), double-click class relabel, two-color blue selection halo.
- **Class management** — mode-aware class row highlighting, per-class visibility toggles, half-transparent unselected points.
- **UI improvements** — auto-maximize on launch, collapsible side panels with toggle buttons, Fusion theme, dark mode support.
- **Export** — batch overlay image export with point annotations.
- **Build** — standalone `.exe` via PyInstaller.

### Dependencies
DotDotGoose is being developed on Ubuntu 22.04 with the following libraries:

* PyQt6 (6.7.1)
* Pillow (10.3.0)
* Numpy (1.26.4)

## Installation
```bash
git clone https://github.com/lu-sugar-tiger/DotDotGoose-fork
python3 -m venv ddg-env
source ddg-env/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./DotDotGoose-fork/requirements.txt
```

## Launching DotDotGoose
```bash
cd DotDotGoose-fork
python3 main.py
```

## Executables

Don't want to install from scratch? [Download the original DotDotGoose and start counting!](https://biodiversityinformatics.amnh.org/open_source/dotdotgoose/)