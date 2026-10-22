# BrianCAD — 2D drafting

An independent desktop drafting application inspired by Vellum's construction workflow. Python 3.9 or newer and Tkinter are required. Geometry is stored in inches. No pip packages are needed.

## Run the current source

From this project folder:

```bash
python3 src/draft.py
```

Keep **all files in `src/` together**: the application now separates geometry, drawing state, and construction methods into modules. The tracked ZIP is the original prototype snapshot and is not the current application.

On Linux Mint, install Tkinter if missing:

```bash
sudo apt install python3-tk
```

On macOS, test your selected interpreter with `python3.13 -m tkinter`, then launch with `python3.13 src/draft.py`. Tcl/Tk must be installed for that interpreter. The application provides macOS Command shortcuts as well as Control shortcuts, but native macOS appearance has not been tested in this environment.

## Bottom parameter fields

Choose a tool family and a construction method. Its numeric parameters appear along the bottom. **Tab / Shift+Tab** moves through them. Clicking a construction point fills its X/Y fields. Fields remain editable; moving the mouse does not overwrite typed values.

- **Use entered point** submits the coordinates for the next construction stage. For splines, it appends the X/Y pair to the point list.
- **Apply / Create**, or Enter in a field, creates geometry from the current fields. For a spline it appends the entered point; **Finish spline**, Enter on the canvas, or right-click commits the spline.
- For lines, editing Length/Angle makes those values define the endpoint. Editing dX/dY uses that displacement. Editing End X/End Y uses that endpoint. The most recently edited field chooses the interpretation.
- Already-picked points can be amended in their fields before clicking the next point. Picked constructions are committed after their final point. Escape cancels pending points; completed objects remain.
- Numeric values are decimal inches; angles are degrees counterclockwise from positive X. Grid preferences additionally accept simple fractions, such as `1/2`.

## Construction methods

| Family | Method | Picks / behavior |
| --- | --- | --- |
| Lines | Two points | Start, endpoint; also supports length/angle and dX/dY entry |
| Lines | Connected points | Each endpoint becomes the next start; Enter on canvas or Escape ends the chain |
| Lines | Offset from line | Pick an existing line, then the offset side/distance; or enter a signed Offset and Apply. Positive is left of source start-to-end direction. |
| Arcs | Center + start + end | Center, start, end direction. The last pick is projected onto the start radius. Clockwise checkbox chooses the sweep. |
| Arcs | Three-point arc | Start, point on the arc, end; the sweep passes through the middle point |
| Arcs | Start tangent + end | Pick the start on an existing line, then the endpoint. Source start-to-end direction defines the initial tangent. |
| Circles | Center + diameter | Pick center then circumference, or enter center and diameter and Apply |
| Circles | Diameter endpoints | Two opposite points |
| Circles | Three-point circle | Three distinct, noncollinear points |
| Circles | Two tangent lines | Pick the exact first contact on a line, then another line near the desired second contact. The second pick chooses the nearby solution; its exact tangency point is calculated. |
| Ovals | Center + corner | Center and corner of an axis-aligned bounding box |
| Ovals | Opposite corners | Opposite corners of an axis-aligned bounding box |
| Ovals | Center + axis + width | Center, major-axis endpoint, point defining perpendicular minor-axis width |
| Ovals | Axis endpoints + width | Opposite major-axis endpoints, then a minor-axis-width point |
| Polygons | Rectangle corners | Opposite corners |
| Polygons | Rectangle center | Center then corner |
| Polygons | Inscribed polygon | Center then vertex; choose Sides (3–200) |
| Polygons | Circumscribed polygon | Center then side midpoint / apothem; choose Sides |
| Splines | Through points | Open Catmull–Rom curve interpolating the picks (2–200 points); finish explicitly |
| Splines | Closed through points | Closed interpolating curve (3–200 points); finish explicitly |
| Splines | Bezier controls | A Bézier curve defined by 2–32 control points; finish explicitly |

Collinear or coincident points and ambiguous tangent cases show an error instead of creating invalid geometry. Tangent methods need existing straight lines; they use the supporting lines where necessary. Circle tangencies to other circles and general spline constraint solving are not implemented. Arbitrary pairs of exact contact points do not always admit a common tangent circle, which is why the second line pick chooses a solution rather than forcing a second exact contact.

## Layers

**Layers...** opens a floating list with eye icons, an active marker, and layer names.

- Single-click highlights a row without changing the active layer.
- Double-click the name to **Set Layer**; double-click the eye to show/hide it. Buttons offer the same actions.
- New and Rename use the Layer name field. Names must be unique.
- Delete reassigns objects to the first remaining layer after confirmation; it does not delete the geometry. At least one layer must remain.
- Hidden-layer objects are excluded from drawing, selection, snapping, transforms, and Fit. Activating a hidden layer shows it. Drawing on a hidden active layer shows it again.

Layer definitions, visibility, active layer, and grid preferences save with the drawing and participate in undo/redo.

## Selection and object editing

Click an outline to select it. **Shift-click** toggles membership in a selection. Drag a box from blank space to select geometry fully contained in the box; Shift adds to the existing selection.

Double-click an object or choose **Edit objects...**. The editor exposes the first selected object's geometry and common attributes: layer, color, lock, line pattern, weight in inches, and control-point display. Polygons and splines expose a point list formatted as `x,y; x,y; ...`. Ellipses expose semi-axis lengths and rotation; arcs expose diameter, start angle, and signed sweep.

Length updates while typing. It is exact for lines, circles, arcs, and polygons; ellipse and spline lengths are sampled approximations. For multiple selections the editor also shows the combined length. **Apply** commits one undoable edit; Close does not apply pending field changes. Locked objects can be inspected and unlocked in this dialog, but transforms and Delete skip them.

## Modify selected geometry

Choose **Modify**, then Move, Rotate, Scale, or Mirror. Set **Copy when transforming** to retain the originals. All selected visible, unlocked geometry changes in one undoable operation.

| Method | Mouse workflow | Numeric fields |
| --- | --- | --- |
| Move | Reference point, destination | dX, dY displacement |
| Rotate | Pivot, reference direction, new direction | Pivot X/Y, signed Angle |
| Scale | Pivot, reference length, new length | Pivot X/Y, positive uniform Factor |
| Mirror | Two points defining the reflection axis | Axis through X/Y at Angle |

Scale is uniform; ellipses, circles, arcs, polygons, and spline definitions retain their analytic/control representation. Mirror reverses an arc's sweep correctly. There is currently no live transformed-object preview; the status bar describes the active pick stage.

## Grid, snaps, and view

**Grid preferences...** sets major spacing (default 1 inch) and subdivisions (default 4, giving quarter-inch minor spacing). Major/minor lines remain anchored to the origin while zooming. Lines denser than 8 pixels are hidden without changing the logical snap spacing.

**Snap to grid** is independent of **Show grid** and **Object snaps / alignment**. Snap priority within 9 screen pixels is: object anchors, existing line-segment/grid crossings, grid intersections, angular alignment, then individual grid lines. Grid-line snaps retain the other coordinate. Angular guides include all eight directions in 45-degree increments through the active line/move start point. Exact typed values are not rounded to snaps.

Wheel zooms around the pointer; middle-button drag pans; **Fit** frames visible geometry. Delete/Backspace removes unlocked selected objects while the canvas has focus. Control+Z / Control+Y undo/redo; Control+S saves; Control+O opens. macOS also supports the equivalent Command shortcuts. Trackpad panning may require a mouse with a middle button.

## Drawing files

Save/Open use JSON in the `briancad-2` format with geometry, styles, layers, active layer, and grid preferences. Original `draft-prototype-1` JSON drawings still open and get a default layer. Save As creates a separate file; saves write a temporary file before replacing the destination. Unsaved changes trigger a discard prompt for New/Open/Exit. VC6 compatibility is outside this implementation.

## Validation

```bash
python3 src/check_geometry.py
python3 -m unittest discover -s src -p 'test_*.py' -v
python3 -m py_compile src/*.py
```

The suite includes geometry/construction, layer/history, legacy and new JSON, grid, and Tkinter workflow tests. Tkinter tests skip if `DISPLAY` is unset (except on macOS, where Tk uses the native display). They were exercised on a temporary Linux X display, including actual layer double-click events, Tab traversal, parameter edits, object dialogs, and save/reopen. Visual inspection covered the drawing window and the layer/object dialogs. Native macOS testing is still needed.

Deferred tools include trim/extend, fillets, dimensions, text, nonuniform scaling, and printing to scale. Splines use explicitly documented interpolation/control algorithms; this is not a claim of exact historical Vellum spline behavior.
