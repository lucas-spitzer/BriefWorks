# Arsenal icon assets

Browser tab icons use the gold rounded mark (white cartridges, transparent corners).
PWA install icons and in-app brand tiles (`ArsenalMark`) keep the gold-on-scarlet three-cartridge mark.

## Marks

**Browser favicon:** white cartridge silhouettes on gold (`#84754E`), rounded square, transparent corners.
Source: `app/public/favicon.svg`.

**PWA / in-app:** three gold (`#84754E`) cartridge silhouettes on scarlet (`#940000`).
Source: `app/public/arsenal-mark.svg` (also the art in the Apple/PWA PNGs).

## Files

| File | Size | Use |
|------|------|-----|
| `favicon.svg` | scalable | Browser tab |
| `favicon.ico` | 16 / 32 / 48 | Legacy browsers, bookmarks |
| `favicon-96x96.png` | 96×96 | Browser favicon (PNG) |
| `arsenal-mark.svg` | scalable | In-app brand mark (`ArsenalMark`) |
| `apple-touch-icon.png` | 180×180 | iOS home screen |
| `web-app-manifest-192x192.png` | 192×192 | PWA install icon |
| `web-app-manifest-512x512.png` | 512×512 | PWA splash / install |
| `manifest.webmanifest` | — | PWA manifest (wired in `index.html`) |

## PWA manifest

`manifest.webmanifest` references all PNG install icons with both `any` and `maskable` purposes.
`start_url` is `/app`; `display` is `standalone`.

## HTML wiring (`index.html`)

- `favicon.ico` + `favicon.svg` + `favicon-96x96.png`
- `apple-touch-icon.png`
- `manifest.webmanifest`
- `theme-color`: `#940000`

## In-app usage

`ArsenalMark` loads `/arsenal-mark.svg` for login, auth callback, security checks, and workspace gate status screens.

## Regenerating

1. Replace the source cartridge artwork.
2. Export browser favicons (`favicon.svg`, `.ico`, `favicon-96x96.png`) separately from PWA/Apple PNGs if the marks differ.
3. Confirm `manifest.webmanifest` and `index.html` still list the same paths.
4. In-app tiles pick up `arsenal-mark.svg` via `ArsenalMark`.
