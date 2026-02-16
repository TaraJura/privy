# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for privy-cli.

Build with:
    pyinstaller privy.spec --clean --noconfirm
"""

from __future__ import annotations

import os

block_cipher = None

a = Analysis(
    ["src/privy_cli/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "gliner",
        "transformers",
        "torch",
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
        "torch.distributed",
        "torch.testing",
        "torch.utils.tensorboard",
        "matplotlib",
        "PIL",
        "IPython",
        "tkinter",
        "unittest",
        "test",
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
