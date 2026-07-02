#!/usr/bin/env bash
set -euo pipefail

app_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
launcher_dir="${HOME}/.local/share/applications"
launcher_path="${launcher_dir}/window-labels.desktop"

mkdir -p "${launcher_dir}"

cat > "${launcher_path}" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Window Labels
Comment=Attach editable labels to running X11 windows
Exec=${app_dir}/window_labels.py
Terminal=false
Categories=Utility;
StartupNotify=false
DESKTOP

chmod +x "${app_dir}/window_labels.py"
chmod +x "${launcher_path}"

echo "Installed ${launcher_path}"
