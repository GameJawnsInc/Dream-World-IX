"""Custom 3D model export/import (field & character GEO models).

Fork-fidelity FIRST: pull a real FF9 field/character model out of the user's install into an editable
skinned FBX-ASCII (mesh + skeleton + textures) that RE-IMPORTS faithfully -- the engine's own
``ModelFactory.CreateModel`` disc-probe loads a loose ``Models/{type}/{geoId}/{geoId}.fbx`` before the
bundle (no DLL). See ``docs/CUSTOM_MODELS.md``.

Offline + read-only on the install; UnityPy is a LAZY import; all output goes to the caller's out_dir
(gitignored) -- zero Square-Enix bytes in the repo.
"""
