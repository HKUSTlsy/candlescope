# Third-party licensing

This repository distributes application source only. It does not vendor dependency code, node_modules, Python packages, bundled binaries, or market data. Install dependencies from their normal registries with the checked-in version pins/lockfile. Dependencies retain their original licenses.

| Dependency | Checked version | Package-declared license |
|---|---|---|
| @luxalgo/vela | 0.8.1 | Apache-2.0, additional NOTICE attribution obligations |
| Vite | 8.3.2 | MIT |
| TypeScript | 6.0.3 | Apache-2.0 |
| ESLint | 10.12.0 | MIT |
| typescript-eslint | 8.71.0 | MIT |
| @playwright/test | 1.63.0 | Apache-2.0 |
| baostock | 0.9.4 | BSD License (PyPI metadata; exact BSD variant not specified) |

Vela: [upstream LICENSE](https://github.com/luxalgo/vela/blob/main/LICENSE) and [NOTICE](https://github.com/luxalgo/vela/blob/main/NOTICE). Copies from the installed 0.8.1 package are included unchanged in VELA-LICENSE and VELA-NOTICE. Every chart display keeps its built-in mark and an equivalent visible Vela link, including focus mode.

[BaoStock 0.9.4 PyPI](https://pypi.org/project/baostock/0.9.4/) declares BSD License; installed metadata has no license text. It is referenced as an installation dependency, not redistributed or relicensed. Verify its exact upstream license text before distributing a package containing BaoStock code/binaries. Software licensing does not grant permission to redistribute source-provided market data.

npm-license-inventory.json inventories metadata of 134 installed npm packages in this preparation environment. Optional platform packages not installed here are outside that local inventory. Indirect packages include MIT, ISC, Apache-2.0, BSD-2/3-Clause, BlueOak-1.0.0 and MPL-2.0. The MPL-2.0 entries are lightningcss and its Darwin ARM64 native build, used by build tooling. None of their source/binaries is vendored here; no upstream code was modified. Binary/bundle releases require a fresh distribution-specific notice/license review, rather than assuming this source-only inventory is sufficient.

Pinned Python installation dependencies also retain their original licenses: pandas 3.0.6 declares BSD 3-Clause; NumPy 2.5.3 metadata lists BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0; python-dateutil 2.9.0.post0 declares Dual License; six 1.17.0 declares MIT. These are installed from registries, not vendored or relicensed. Requirements need Python 3.12+ (clean validation used 3.14).
