# AutoClicker

**[English](#english) | [Português](#português)**

![AutoClicker](docs/screenshot.png)

---

## English

A Linux autoclicker with a graphical interface, inspired by GS Auto Clicker
(Windows): set the interval between clicks in milliseconds and a hotkey to
toggle it on/off, and it works even while another window (or game) has
focus.

### How it works

- **UI**: Tkinter, with a custom title bar (minimize, close, drag) since
  many Wayland compositors don't draw any decoration on Tk/XWayland windows.
- **Simulated clicks**: via [`ydotool`](https://github.com/ReimuNotMoe/ydotool),
  which works on both X11 and Wayland.
- **Global hotkey**: reads the keyboard directly via
  [`python-evdev`](https://github.com/gvalkov/python-evdev), so it works
  even without focus on the AutoClicker window.
- **Dragging the window**: uses `hyprctl cursorpos` when available
  (Hyprland), because querying the cursor position via X11 while the
  window itself is being moved causes a coordinate-corruption bug on
  Wayland compositors (the window "teleports" instead of smoothly
  following the mouse). On other environments it falls back to a plain
  X11 query (`winfo_pointerx/y`), which works fine on native X11 but may
  not be perfectly smooth on other Wayland compositors — untested outside
  of Hyprland.

### Installation

```bash
git clone https://github.com/Felipe-Luvizotto/autoclicker.git
cd autoclicker
./install.sh
```

The `install.sh` script:

1. Installs system dependencies (`tk`, `python-evdev`, `ydotool`) —
   auto-detects Arch (`pacman`), Debian/Ubuntu (`apt`), Fedora (`dnf`) and
   openSUSE (`zypper`).
2. Adds your user to the `input` group (needed to read the keyboard and
   simulate clicks without running as root).
3. Enables the `ydotoold` service (`systemctl --user enable --now ydotool`).
4. Creates an "AutoClicker" shortcut in your application menu.

**After installing, log out and back in (or reboot)** — the `input`
group change only takes effect on new sessions.

#### Other distros / unsupported package managers

Install manually: `tk` (Python's Tcl/Tk bindings), `python-evdev` (or
`pip install --user evdev`), and `ydotool`. Then run steps 2-4 from
`install.sh` by hand (see the script).

### Usage

Open it from the application menu ("AutoClicker") or run `./run.sh`.

- **Interval between clicks (ms)**: lower = faster clicking (100ms = 10
  clicks/second).
- **Hotkey**: click the button and press the key you want (default: `F6`).
  Works from any window, not just while AutoClicker is focused.
- **Dragging the window**: click and hold the dark title bar at the top.

### Requirements

- Linux (X11 or Wayland)
- Python 3
- `ydotool` + `ydotoold` running
- User in the `input` group

### License

MIT

---

## Português

Um autoclicker para Linux com interface grafica, inspirado no GS Auto Clicker
(Windows): defina o intervalo entre cliques em milissegundos e uma tecla de
atalho para ligar/desligar, e ela funciona mesmo com outra janela (ou jogo)
em foco.

### Como funciona

- **Interface**: Tkinter, com uma barra de titulo customizada (minimizar,
  fechar, arrastar) ja que muitos compositores Wayland nao desenham
  decoracao nenhuma em janelas Tk/XWayland.
- **Clique simulado**: via [`ydotool`](https://github.com/ReimuNotMoe/ydotool),
  que funciona tanto em X11 quanto em Wayland.
- **Tecla de atalho global**: le o teclado diretamente via
  [`python-evdev`](https://github.com/gvalkov/python-evdev), entao funciona
  mesmo sem foco na janela do AutoClicker.
- **Arrastar a janela**: usa `hyprctl cursorpos` quando disponivel (Hyprland),
  pois consultar a posicao do cursor via X11 enquanto a propria janela esta
  sendo movida causa um bug de coordenadas erradas em compositores Wayland
  (a janela "teleporta" em vez de seguir o mouse suavemente). Em outros
  ambientes, cai para uma consulta X11 padrao (`winfo_pointerx/y`), que
  funciona bem em X11 nativo mas pode nao ser perfeitamente suave em outros
  compositores Wayland — nao testado fora do Hyprland.

### Instalacao

```bash
git clone https://github.com/Felipe-Luvizotto/autoclicker.git
cd autoclicker
./install.sh
```

O script `install.sh`:

1. Instala as dependencias de sistema (`tk`, `python-evdev`, `ydotool`) —
   detecta automaticamente Arch (`pacman`), Debian/Ubuntu (`apt`), Fedora
   (`dnf`) e openSUSE (`zypper`).
2. Adiciona seu usuario ao grupo `input` (necessario para ler o teclado e
   simular cliques sem precisar rodar como root).
3. Habilita o servico `ydotoold` (`systemctl --user enable --now ydotool`).
4. Cria um atalho "AutoClicker" no menu de aplicativos.

**Depois de instalar, faca logout/login (ou reinicie)** — a mudanca de
grupo (`input`) so vale para sessoes novas.

#### Outras distros / gerenciadores de pacote nao suportados

Instale manualmente: `tk` (bindings Tcl/Tk para Python), `python-evdev` (ou
`pip install --user evdev`), e `ydotool`. Depois rode os passos 2-4 do
`install.sh` manualmente (veja o script).

### Uso

Abra pelo menu de aplicativos ("AutoClicker") ou rode `./run.sh`.

- **Intervalo entre cliques (ms)**: quanto menor, mais rapido clica (100ms
  = 10 cliques/segundo).
- **Tecla de atalho**: clique no botao e aperte a tecla desejada (padrao:
  `F6`). Funciona em qualquer janela, nao so quando o AutoClicker esta em
  foco.
- **Arrastar a janela**: clique e segure a barra de titulo escura no topo.

### Requisitos

- Linux (X11 ou Wayland)
- Python 3
- `ydotool` + `ydotoold` rodando
- Usuario no grupo `input`

### Licenca

MIT
