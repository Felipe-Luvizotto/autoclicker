#!/usr/bin/env bash
# Instalador do AutoClicker para Linux (X11 ou Wayland).
#
# Detecta a distro, instala as dependencias de sistema necessarias,
# adiciona o usuario ao grupo 'input' (necessario para ler o teclado e
# simular cliques sem precisar de root), habilita o daemon do ydotool
# e cria um atalho no menu de aplicativos.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Instalando dependencias de sistema..."

install_deps() {
    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --needed --noconfirm tk python-evdev ydotool
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3-tk python3-evdev ydotool
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3-tkinter python3-evdev ydotool
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y python3-tk python3-evdev ydotool
    else
        echo "Gerenciador de pacotes nao reconhecido automaticamente."
        echo "Instale manualmente: tk (tkinter), python3-evdev, ydotool."
        return 1
    fi
}

install_deps

# python-evdev pode nao existir em alguns repositorios; garante via pip.
if ! python3 -c "import evdev" >/dev/null 2>&1; then
    echo "==> python-evdev nao encontrado via pacote de sistema, tentando pip..."
    python3 -m pip install --user evdev || {
        echo "Nao foi possivel instalar 'evdev'. A tecla de atalho global nao vai funcionar."
    }
fi

echo "==> Adicionando $USER ao grupo 'input' (necessario para ler o teclado e simular cliques)..."
if ! id -nG "$USER" | grep -qw input; then
    sudo usermod -aG input "$USER"
    NEEDS_RELOGIN=1
else
    NEEDS_RELOGIN=0
fi

echo "==> Habilitando o servico ydotoold..."
systemctl --user enable --now ydotool.service 2>/dev/null || {
    echo "Aviso: nao consegui habilitar o servico 'ydotool.service' automaticamente."
    echo "Rode 'ydotoold' manualmente ou configure o servico do seu sistema."
}

echo "==> Criando atalho no menu de aplicativos..."
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/autoclicker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=AutoClicker
Comment=Autoclicker configuravel com tecla de atalho, estilo GS Auto Clicker
Exec=$SCRIPT_DIR/run.sh
Terminal=false
Categories=Utility;
EOF

chmod +x "$SCRIPT_DIR/run.sh"

echo
echo "==> Instalacao concluida."
if [ "$NEEDS_RELOGIN" = "1" ]; then
    echo
    echo "IMPORTANTE: voce foi adicionado ao grupo 'input' agora."
    echo "Faca LOGOUT e LOGIN de novo (ou reinicie) antes de usar o AutoClicker,"
    echo "senao a tecla de atalho e o clique nao vao funcionar."
fi
echo
echo "Para abrir: procure 'AutoClicker' no menu de aplicativos, ou rode:"
echo "  $SCRIPT_DIR/run.sh"
