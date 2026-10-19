# Local Noto Serif SC

The game uses this local copy of Noto Serif SC for body text at weights 400 and 600.
The title font, Ma Shan Zheng, is already bundled separately at `../../tex/msz.woff2`.

`fonts.css` preserves Google's original `unicode-range` rules and `font-display: swap`.
There are 202 face declarations and 101 unique WOFF2 files (about 5.75 MiB total).
The browser downloads only the character subsets needed by the visible text, and
the two weights share the same source files as in the original stylesheet.
Every runtime font URL is relative to this folder; the game does not contact
Google Fonts.

Source stylesheet: https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600&display=swap

License: SIL Open Font License 1.1, included verbatim in `OFL.txt`.
Official license source: https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifsc/OFL.txt

Version and source URLs, file sizes and SHA-256 hashes are in `manifest.json`.
Font binaries are unmodified. Keep `OFL.txt` with redistributed copies.

To refresh from the official source, run `perf/vendor-fonts.ps1` from PowerShell 7
in the project root. This development script needs Internet access; the game does
not need it for fonts. Validate the resulting files with `node perf/check-local-fonts.cjs`.
