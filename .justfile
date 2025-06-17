ruffle:
    ruff check --select I --fix
    ruff format

upgrade:
    uv lock --upgrade
    uv sync

build:
    uv sync
    uv build

build-app:
    uv run pyinstaller orcAI.spec --noconfirm

build-dmg:
    uv run dmgbuild -s dmg_settings.py "orcAI" orcai.dmg

build-all: build build-app build-dmg

run:
    uv run orcaigui
