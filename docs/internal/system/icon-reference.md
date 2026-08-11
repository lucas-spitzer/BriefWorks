# Foundry icon assets

Icons exported from [RealFaviconGenerator](https://realfavicongenerator.net) (Canva source).
Used for favicons, Apple touch icons, and PWA install.

## Files

| File | Size | Use |
|------|------|-----|
| `favicon.svg` | scalable | Modern browser tab icon |
| `favicon.ico` | multi-size | Legacy browsers, bookmarks |
| `favicon-96x96.png` | 96×96 | Browser favicon (PNG) |
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

## Regenerating

1. Update the mark in Canva.
2. Re-export through RealFaviconGenerator.
3. Replace every file in this folder (keep filenames).
4. Confirm `manifest.webmanifest` and `index.html` still list the same paths.
