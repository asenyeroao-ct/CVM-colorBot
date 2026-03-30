# Makcu Controller API

## Serial Commands

- `ctl.stick(rx,ry)`
  - signed ints only
  - range: `-32767` to `32767` per axis
  - `rx`: `+right` / `-left`
  - `ry`: `+down` / `-up`
  - example: `ctl.stick(12000,-8000)`
  - do not send floats, missing args, or named values
  - `ctl.stick(0,0)` will not clear overrides

- `ctl.clear()`
  - clears active stick override
  - send: `ctl.clear()`

- `ctl.state()`
  - returns: `ctl.state(buttons,lt,rt)`
  - `buttons` = `uint16` bitmask
  - `lt` / `rt` = `0-255`
  - example response: `ctl.state(4096,0,182)`

## Integration Notes

- This repo uses `ctl.stick(...)` for movement output.
- This repo uses `ctl.clear()` to release the stick override after each short movement pulse.
- Current public docs only expose stick/state commands, so mouse click and keyboard output fall back to local Win32 SendInput behavior.
