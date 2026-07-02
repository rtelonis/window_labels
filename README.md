# Window Labels

A small Kubuntu/X11 label utility for attaching editable labels to running windows.
It is intended for visually identifying `gnome-terminal` sessions, but it can
attach to any normal X11 window.

## Requirements

- Kubuntu 24.04 running a Plasma X11 session
- Python 3
- PyQt5 (`python3-pyqt5`)
- X11 libraries (`libx11-6`, normally already installed)

If PyQt5 is missing:

```bash
sudo apt install python3-pyqt5
```

Wayland is not supported because it intentionally prevents normal applications
from inspecting and following other windows.

## Run

```bash
./window_labels.py
```

Click `Pick Window`, then click the terminal or other window you want to label.
The label is editable. Drag the label by its header to reposition it relative to
the attached window. When the attached window moves, the label follows.

Right-click a label to change its color or delete it.

Labels are saved to:

```text
~/.config/window-labels/labels.json
```

## Install A Desktop Launcher

```bash
./install_desktop_launcher.sh
```

After installation, launch `Window Labels` from the application menu.
# ai_utils
