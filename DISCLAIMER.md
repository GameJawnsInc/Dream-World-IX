# Disclaimer

**Dream World IX** (the `ff9mapkit` toolkit and everything in this repository) is an **unofficial,
fan-made project.**

- It is **not affiliated with, endorsed by, or sponsored by Square Enix.** *FINAL FANTASY IX* and
  *FINAL FANTASY* are trademarks of Square Enix Holdings Co., Ltd. All FF9 names, characters, art,
  and game data are the property of their respective owners.

- It **ships no FINAL FANTASY IX game data.** This is an authoring *tool*. Like an emulator or a
  ROM-hack patcher, it operates only on assets read from **a copy of the game you legally own**. The
  base assets it needs are regenerated from your own install by `ff9mapkit extract-templates`; the
  repository and the published package contain none of Square Enix's copyrighted bytes. For exactly
  how this works (copy/insert patches + SHA-256 manifest, never game bytes), see
  [`ff9mapkit/docs/PROVENANCE.md`](ff9mapkit/docs/PROVENANCE.md).

- It **does not enable or condone piracy.** You must own a legitimate copy of *FINAL FANTASY IX*
  (e.g. the Steam release) to use it. Nothing here distributes the game or any part of it.

- It modifies the game **at your own risk.** Always back up your clean game install before deploying
  any mod. The software is provided "as is", without warranty of any kind (see [LICENSE](LICENSE)).

The toolkit's own source code is released under the [MIT License](LICENSE). This grants no rights to
FINAL FANTASY IX game data. Background art and field designs you create with the toolkit are your own.

The bundled engine patches under [`memoria-patches/`](memoria-patches/) modify the
[Memoria engine](https://github.com/Albeoris/Memoria), which is itself distributed under the MIT
License (© 2017 Albeoris).
