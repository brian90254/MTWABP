# FastHardwareRuntime — GDScript API

Call these on the `FAST` node from GDScript (e.g. `fast.GdStartup(...)`). Connect to the signals
for callbacks (e.g. `fast.connect("HardwareReady", _on_ready)`). Enum arguments are passed as
their integer index — the relevant values are noted on each parameter.

## Contents

**Signals**

- [HardwareReady](#hardwareready)
- [SwitchActivity](#switchactivity)

**Methods**

- [GdStartup](#gdstartup)
- [GdIsInitialized](#gdisinitialized)
- [GdGetMachineType](#gdgetmachinetype)
- [GdWatchSwitch](#gdwatchswitch)
- [GdUnwatchSwitch](#gdunwatchswitch)
- [GdRegisterSpoofKey](#gdregisterspoofkey)
- [GdIsSwitchDown](#gdisswitchdown)
- [GdIsSwitchUp](#gdisswitchup)
- [GdSetPixelColour](#gdsetpixelcolour)
- [GdSetPixelColours](#gdsetpixelcolours)
- [GdSetAllPixelsToColour](#gdsetallpixelstocolour)
- [GdTurnOffPixels](#gdturnoffpixels)

---

## Signals

### HardwareReady

```gdscript
signal HardwareReady(resultCode: int)
```

Emitted once startup finishes. Connect to it to know when the hardware is ready.

**Parameters**

- `resultCode` — `int` — A FAST.eResult value; 0 (SUCCESS) means startup succeeded.

---

### SwitchActivity

```gdscript
signal SwitchActivity(switchIndex: int, switchEvent: int)
```

Emitted whenever a switch being watched with GdWatchSwitch changes state.

**Parameters**

- `switchIndex` — `int` — The zero-based global index of the switch that changed.
- `switchEvent` — `int` — A FAST.eSwitchEvent value (1 = ON_DOWN/CLOSED, 2 = ON_UP/OPENED).

---

## Methods

### GdStartup

```gdscript
func GdStartup(NodeBoards: PackedInt32Array, ExpansionBoards: PackedInt32Array, ProductionBuild: bool) -> void
```

Starts the FAST hardware. The HardwareReady signal fires when initialization finishes.

**Parameters**

- `NodeBoards` — `PackedInt32Array` — Ordered node-board indices (FAST.eNodeBoards values), e.g. [0] for FP_CAB0001.
- `ExpansionBoards` — `PackedInt32Array` — Ordered expansion-board indices (FAST.eExpansionBoards values), e.g. [0] for NEURON.
- `ProductionBuild` — `bool` — True for a production build; false while developing.

---

### GdIsInitialized

```gdscript
func GdIsInitialized() -> bool
```

Checks whether the hardware has finished starting up.

**Returns** — True once startup has completed; false otherwise.

---

### GdGetMachineType

```gdscript
func GdGetMachineType() -> int
```

Gets the connected machine type.

**Returns** — A FAST.eNetStyle value (0 = UNKNOWN, 2 = MODERN, 3 = RETRO_11, 4 = RETRO_89, 5 = RETRO_95).

---

### GdWatchSwitch

```gdscript
func GdWatchSwitch(SwitchIndex: int) -> void
```

Starts reporting a switch's state changes through the SwitchActivity signal.

**Parameters**

- `SwitchIndex` — `int` — The zero-based global index of the switch to watch.

---

### GdUnwatchSwitch

```gdscript
func GdUnwatchSwitch(SwitchIndex: int) -> void
```

Stops reporting a switch previously passed to GdWatchSwitch.

**Parameters**

- `SwitchIndex` — `int` — The zero-based global index of the switch to stop watching.

---

### GdRegisterSpoofKey

```gdscript
func GdRegisterSpoofKey(SwitchIndex: int, SpoofKey: int) -> void
```

Maps a keyboard key to a switch so switches can be exercised from the desktop.

**Parameters**

- `SwitchIndex` — `int` — The zero-based global index of the switch to spoof.
- `SpoofKey` — `int` — A Godot Key value (e.g. KEY_A) that will act as this switch.

---

### GdIsSwitchDown

```gdscript
func GdIsSwitchDown(SwitchIndex: int) -> bool
```

Tests whether a switch is currently closed/down.

**Parameters**

- `SwitchIndex` — `int` — The zero-based global index of the switch to test.

**Returns** — True if the switch is down; false otherwise.

---

### GdIsSwitchUp

```gdscript
func GdIsSwitchUp(SwitchIndex: int) -> bool
```

Tests whether a switch is currently open/up.

**Parameters**

- `SwitchIndex` — `int` — The zero-based global index of the switch to test.

**Returns** — True if the switch is up; false otherwise.

---

### GdSetPixelColour

```gdscript
func GdSetPixelColour(Index: int, NewColour: Color, Dest: int) -> void
```

Sets a single pixel (LED) to a colour.

**Parameters**

- `Index` — `int` — The zero-based pixel index.
- `NewColour` — `Color` — The colour to display.
- `Dest` — `int` — Destination board: a FAST.eExpansionDestinations value (0 = NEURON, 1 = EXPANSION).

---

### GdSetPixelColours

```gdscript
func GdSetPixelColours(StartIndex: int, NewColours: PackedColorArray, Dest: int) -> void
```

Sets a run of pixels (LEDs) starting at a given index.

**Parameters**

- `StartIndex` — `int` — The zero-based index of the first pixel to set.
- `NewColours` — `PackedColorArray` — The colours to write, one per consecutive pixel (a PackedColorArray).
- `Dest` — `int` — Destination board: a FAST.eExpansionDestinations value (0 = NEURON, 1 = EXPANSION).

---

### GdSetAllPixelsToColour

```gdscript
func GdSetAllPixelsToColour(NewColour: Color, Dest: int) -> void
```

Sets every pixel (LED) on a destination to the same colour.

**Parameters**

- `NewColour` — `Color` — The colour to apply to all pixels.
- `Dest` — `int` — Destination board: a FAST.eExpansionDestinations value (0 = NEURON, 1 = EXPANSION).

---

### GdTurnOffPixels

```gdscript
func GdTurnOffPixels(Dest: int) -> void
```

Turns every pixel (LED) on a destination off.

**Parameters**

- `Dest` — `int` — Destination board: a FAST.eExpansionDestinations value (0 = NEURON, 1 = EXPANSION).

---

_Generated from FAST_GodotScript.cs on 2026-07-13 08:36._
