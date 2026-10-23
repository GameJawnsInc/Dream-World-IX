"""``FF9SpecialEffectPlugin.dll`` -- THE ONE table of plugin builds whose internal memory layout is known.

Three consumers read the plugin's memory at fixed offsets, and all three must agree on which build those
offsets belong to:

  * ``summons/deploy.py`` refuses to arm ``[SfxHybrid]`` unless the install's plugin hashes to a build
    listed here (the s58 hybrid drive reads the summon record and WRITES the body-hide mask through it);
  * ``studies/custom-summons/headless/sfx_host.py`` reads the summon slot and the GTE camera only on a
    build listed here (it loads this file by path, so it stays import-free);
  * the engine -- the s52/s53/s58 RVAs and the s152 ``SfxPluginIdentity`` PE pins under
    ``memoria-patches/`` -- is C# and cannot import this; ``tests/test_summon_deploy.py`` parses those
    patches and fails on any drift between them and this table.

Add a build only after its offsets are MEASURED on it (a GOG or other-store build, an updated plugin):
an entry here is what lets the drive write into that DLL's memory. Until then such an install is
refused, and the DLL-free overlay summon lane is the way to go there.
"""

PLUGIN_NAME = "FF9SpecialEffectPlugin.dll"

#: sha256 -> the build's identity (arch + the PE header fields s152 checks in memory) and its layout.
#: ``in_game`` says whether casts on this build have exercised the offsets in game. The x64 build is the
#: one every recorded cast ran (and the headless host reproduces the in-game s53 Bahamut capture frame
#: for frame on it). The x86 offsets were re-derived statically
#: (``studies/custom-summons/thomas-swap/disasm/B5-x86-crosscheck.md``) and never cast.
PINNED_BUILDS = {
    "5e01f899e9090fc720f4fd563648f216f5f1f088c902d0f80aa04d34f31d43cd": {
        "arch": "x64", "linked": "2016-10-19", "in_game": True,
        "machine": 0x8664, "stamp": 0x58075FAB, "size_of_image": 0x627000,
        "summon_rec": 0x220830,      # summonModels[0] (length 1), stride 0x58
        "summon_active": 0x50,       # u8, 0 = no summon this frame
        "data_bones": 0x38,          # SummonData -> composed node MATRIX array (node 0 = drawn transform)
        "data_hide_mask": 0x20,      # u32 body-hide mask -- the s58 drive's one WRITE
        "gte_ofx": 0x211FA0, "gte_ofy": 0x211FA4, "gte_h": 0x211FA8,
        "view_matrix": 0x1C1DC8,     # native world->view MATRIX (s53 PSXCAM): 3x3 s16 fp12, s32 t @+0x14
    },
    "8635255d78cde4c839cc26c11d114f1e64b96553f08828f4fd4bd1900780a87e": {
        "arch": "x86", "linked": "2016-10-19", "in_game": False,
        "machine": 0x014C, "stamp": 0x580763E9, "size_of_image": 0x611000,
        "summon_rec": 0x20869C,      # summonModels[0] (length 1), stride 0x54
        "summon_active": 0x4C,
        "data_bones": 0x20,
        "data_hide_mask": 0x14,
        # no GTE camera RVAs: never derived on x86 (s53's PSXCAM row is x64-only)
    },
}


def pinned_for(arch: str) -> dict:
    """``{sha256: pin}`` for one arch (``"x64"`` / ``"x86"``)."""
    return {sha: pin for sha, pin in PINNED_BUILDS.items() if pin["arch"] == arch}
