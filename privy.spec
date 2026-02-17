# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for privy-cli.

Build with:
    pyinstaller privy.spec --clean --noconfirm
"""

from __future__ import annotations

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# gliner is lazily imported (try/except), so PyInstaller's analysis misses it.
# collect_all grabs the package's submodules, data files, and binaries.
_packages_to_collect = ["gliner", "transformers", "torch"]
_all_datas = []
_all_binaries = []
_all_hiddens = []
for _pkg in _packages_to_collect:
    _d, _b, _h = collect_all(_pkg)
    _all_datas += _d
    _all_binaries += _b
    _all_hiddens += _h

a = Analysis(
    ["src/privy_cli/__main__.py"],
    pathex=["src"],
    binaries=_all_binaries,
    datas=_all_datas,
    hiddenimports=_all_hiddens + [
        "numpy",
        "onnxruntime",
        "sentencepiece",
        "tokenizers",
        "huggingface_hub",
        "safetensors",
        "filelock",
        "fsspec",
        "regex",
        "packaging",
        "pyyaml",
        "requests",
        "tqdm",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "PIL",
        "IPython",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

# Remove CUDA/ROCm binaries — not needed on macOS.
a.binaries = [
    b for b in a.binaries
    if not any(
        x in b[0].lower()
        for x in ("cuda", "cudnn", "nccl", "nvrtc", "rocm", "cublas", "cufft", "curand", "cusparse", "cusolver")
    )
]

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="privy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=os.environ.get("CODESIGN_IDENTITY", ""),
    entitlements_file="entitlements.plist",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name="privy",
)
