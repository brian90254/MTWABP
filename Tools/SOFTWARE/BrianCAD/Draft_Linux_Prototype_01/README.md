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
- **Apply / Create**, or Enter in a field, creates geometry from the current fields. For a spline it appends the entered point; **Finish spline** or Enter on the canvas commits the spline. **Right-click** finishes a pending spline and stays in Splines; a subsequent right-click with no pending points returns to Select. In other tools, right-click cancels pending picks/previews and returns to Select, retaining completed geometry and the selection. An incomplete spline keeps its points and reports what is needed. On macOS, Control-click has the same behavior.
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
| Arcs | Start tangent + end | Pick the arc start, a tangent direction point, then the arc endpoint. The tangent guide points from the first pick toward the second; only the arc is created. Endpoint side determines clockwise/counterclockwise automatically (the center-arc Clockwise checkbox does not apply). |
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

Collinear or coincident points and ambiguous tangent cases show an error instead of creating invalid geometry. The tangent-arc method uses three freely chosen points and needs no existing geometry. The start and tangent direction point must differ, and the arc endpoint must be off their tangent line. Circle tangent construction still needs existing straight lines and uses their supporting lines where necessary. Circle tangencies to other circles and general spline constraint solving are not implemented. Arbitrary pairs of exact contact points do not always admit a common tangent circle, which is why the second line pick chooses a solution rather than forcing a second exact contact.

## Layers

**Layers...** opens a floating list with eye icons, an active marker, and layer names.

- Single-click highlights a row without changing the active layer.
- Double-click the name to **Set Layer**; double-click the eye to show/hide it. Buttons offer the same actions.
- New and Rename use the Layer name field. Names must be unique.
- Delete reassigns objects to the first remaining layer after confirmation; it does not delete the geometry. At least one layer must remain.
- Hidden-layer objects are excluded from drawing, selection, snapping, transforms, and Fit. Activating a hidden layer shows it. Drawing on a hidden active layer shows it again.

Layer definitions, visibility, active layer, and grid preferences save with the drawing and participate in undo/redo.

## Trim

1. With **Select**, select one or more cutting boundaries, then choose **Trim** in the toolbox. Selected handles promote their whole owning object to a boundary. The active boundaries stay highlighted orange.
2. Click directly on the portion of a line, circle, arc, oval, or spline to remove. The clicked interval between crossings or tangent contacts is removed; the retained pieces keep their layer, pen settings, and other attributes. Active boundaries remain unchanged and available for repeated clicks on other targets.
3. **Right-click or Escape** returns to Select. Each successful click is one undo step. Undo/redo exits Trim; reselect boundaries to start another trim session.

For example, select a line crossing a circle, choose Trim, and click the unwanted side of the circle to leave an arc. Alternatively, select the circle and click the middle of a crossing line to leave two outside segments. Clicking an outside segment instead removes that end up to the nearest crossing; click the other outside section separately if desired. Multiple boundaries divide a target into intervals, and only the clicked interval is removed.

Trim supports **lines, circles, arcs, ovals, and splines** as targets and cutting boundaries. Polygon edges can also be cutting boundaries; polygon targets are not supported. Lines and arcs use their **finite drawn extents**, without automatic extension. Hidden geometry is ignored. Locked objects can be boundaries but cannot be trimmed. A trimmed oval remains an exact elliptical arc, with Start/Sweep angle fields in the object editor and center/endpoint handles. Spline trimming uses exact Bézier subdivision: a retained section spanning several Catmull–Rom spans becomes several editable Bézier pieces. Those pieces preserve the original curve and can be trimmed again. Layer and pen settings are preserved, and all pieces from one click share one undo step. Tangent contacts count as cutting points, including a line ending at its tangent contact with a circle or arc. Two distinct contacts on a closed circle can leave an arc. With just one contact on any closed circle, oval, or closed spline, the entire closed curve is the removable interval, so clicking it deletes it. Coincident curves and targets with no usable contact produce no geometry/history changes. Line/conic and conic/spline contacts are solved on the actual curves; spline/spline contacts use bounded adaptive subdivision and refinement. Overlapping or excessively complex spline boundaries that cannot be resolved reliably report an error before changing the drawing.

## Selection and object editing

The Select tool keeps its arrow-with-tail toolbox icon and uses an explicit arrow-with-tail mouse pointer on the canvas. Its tip follows the raw mouse position independently of the snap marker. Other tools retain their standard mouse pointer.

Click an outline **or any of its handles** to select the whole object. A plain click on an already-selected handle also promotes its owner to whole-object selection; pressing and dragging that handle preserves the partial selection instead. **Shift-click** toggles whole-object membership.

Drag a window from blank space in either direction:

- Objects **wholly contained** in the window become whole-object selections; they are not decomposed into selected handles.
- For other objects, only editable handles inside the window are selected. For example, a small window around a circle's right-hand radius point selects that handle, leaving its center fixed.
- Shift adds the window's results to the existing selection. Whole-object selection takes precedence over that object's handle subset.

Whole-object selections are highlighted orange. Selected handles are filled orange; unselected handles are hollow. The status bar separately counts whole objects and handles. Selection itself is transient and does not mark a drawing unsaved.

With **Select** still active, press and drag a selected object or selected handle to move the entire current selection (including mixed whole-object and handle selections). The snapped point at the initial press becomes the movement handle. Snaps remain live during the drag, the drawing previews the result, and release commits it as **one undo step**. A small 4-pixel movement threshold separates clicks from drags. Escape discards the preview. Invalid deformations, such as collapsing a line or circle to zero size, leave the original drawing intact.

Editable handles are distinct from snap points:

| Geometry | Editable handles | Partial-handle behavior |
| --- | --- | --- |
| Line | Two endpoints | Selected endpoints move; unselected endpoints stay fixed |
| Circle | Center and one radius point (initially positive X) | Radius handle changes radius and retains its picked direction; center handle translates the circle |
| Arc | Center, start, through point, end | Rim handles reconstruct a circular arc through the three points; unselected rim points remain fixed. Center translates the arc. |
| Ellipse | Center, positive-axis endpoints | Center translates it; axis handles change size/rotation while preserving perpendicular axes. Minor-axis movement is projected perpendicular to the major axis. |
| Polygon | Vertices | Selected vertices move |
| Spline | Fit or Bézier control points | Selected defining points move |

Circles' four global horizontal/vertical **quadrants remain snap targets**. Arcs, including trimmed circles, also offer those quadrant points when they lie on the retained sweep. These are snap targets, not four independent editable radius points. Midpoints are also snap targets rather than independent line endpoints. Moving a center handle necessarily moves the dependent curve. The explicit Modify tools still operate on whole-object selections; use Select-drag for handle deformation. Delete removes whole-object selections only.

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

Scale is uniform; ellipses, circles, arcs, polygons, and spline definitions retain their analytic/control representation. Mirror reverses an arc's sweep correctly. The explicit Modify tools commit after their final pick without a live geometry preview; Select-drag provides a live movement preview.

## Grid, snaps, and view

**Grid preferences...** sets major spacing (default 1 inch) and subdivisions (default 4, giving quarter-inch minor spacing). Major/minor lines remain anchored to the origin while zooming. Lines denser than 8 pixels are hidden without changing the logical snap spacing. Both levels use the same color; major lines have a denser dotted pattern and minor lines use fewer dots.

**Recent snap alignment guides:** Hovering or clicking a discrete object snap remembers its location. The four most recent distinct locations are kept; revisiting one makes it most recent. Eligible snaps include endpoints, midpoints, centers, quadrants, tangent/perpendicular contacts, vertices, fit/control points, and object intersections. Grid-derived snaps (including line/grid intersections), ordinary origin snaps and continuously moving on-line/on-curve projections do not fill the history. An object anchor at the origin still counts as an object point.

When the pointer's current drawing position is within 6 screen pixels of a remembered X or Y coordinate, an immediate dotted guide spans the canvas: a vertical guide labeled **align x** shares X, and a horizontal guide labeled **align y** shares Y. Both can appear together. These guides are also snap targets: an **align x** snap fixes X while leaving Y free, and **align y** fixes Y while leaving X free. When both are within tolerance, both coordinates snap, even if they come from different remembered points. The nearest remembered coordinate wins on each axis. Each guide also independently offers point snaps where it intersects the grid or a visible object; a second remembered guide is not required. Vertical guides intersect horizontal grid lines, and horizontal guides intersect vertical grid lines. Guide/object intersections use the actual finite line, arc, polygon, circle, ellipse, or spline geometry, including tangent contacts. Crossings of remembered vertical and horizontal guides are point targets as well. Nearby crossing targets take priority over plain guide projections. Grid-derived crossings require Snap to grid; all alignment targets require Object snaps / alignment. Derived intersection targets do not enter snap memory. Exact typed coordinates remain authoritative. Alignment snaps do not enter the four-point history. While moving geometry, remembered points on that geometry are excluded from both guides and snap targets to avoid sticking to its old position. Guides hide when the pointer leaves the canvas, during panning, or when Object snaps / alignment is disabled. History remains available within the same tool, including after completing a drawing operation or cancelling pending picks. Changing tools or construction methods, or starting/opening a drawing, clears it. History is transient and is not saved in drawing files.

**Tangent snapping:** After choosing the start of a Two points or Connected points line, move near a tangent contact on an existing circle, arc, oval, or spline. The endpoint snaps to the exact contact and the hover label reads **tangent**. Contacts are calculated from the current starting X/Y fields; arcs offer only contacts on their actual sweep. A start inside or on a circle/oval offers no nonzero tangent segment. Oval tangents respect rotation and both radii; spline tangents are solved on the actual Bézier/Catmull–Rom curve rather than display chords. Hidden geometry is excluded, and disabling Object snaps / alignment disables tangent snaps.

**Perpendicular snapping:** While choosing the endpoint of a Two points or Connected points line, move near a point where the line from its current starting X/Y is perpendicular to an existing line or curve. The endpoint snaps there and the label reads **perpendicular**. Finite line segments, polygon edges, circles, arcs, ovals, and splines are supported. Multiple valid normal contacts can be offered; choose by hovering near the intended one. Feet beyond a line/arc extent and zero-length contacts are omitted. Undefined tangents at spline cusps and continuous families of equivalent contacts are not discrete targets. Contact calculations are cached for a fixed object/start point. Object snaps / alignment controls both tangent and perpendicular snapping.

**Snap to grid** is independent of **Show grid** and **Object snaps / alignment**. Snap priority within 9 screen pixels is: nearest tangent/perpendicular contacts while drawing a line, object anchors (including circle and arc quadrants), remembered X/Y alignment guides, existing line-segment/grid crossings, grid intersections, points **on an object**, angular alignment, then individual grid lines. Grid-line snaps retain the other coordinate. Angular guides include all eight directions in 45-degree increments through the active line/move start point. Exact typed values are not rounded to snaps. The snap target is a small black **×** centered on the exact snap location. Snapping and the target marker remain immediate, but the descriptive label appears only after the pointer has been stationary for **0.6 seconds**. Moving, leaving the canvas, panning, or cancelling hides the label and resets the delay. Labels use a smaller grey font, including while a drag is paused. Hovering near a line or curve away from another snap point shows **on line** or **on curve** and projects onto its geometry. Line/circle/arc projections are analytic; ellipse/spline projections are refined numerically rather than snapping to rendered polyline chords. During Select-drag, moving objects are excluded from target snapping so the selection does not stick to its own previous position; other visible geometry and the origin/grid remain available.

Wheel zooms around the pointer; middle-button drag pans; **Fit** frames visible geometry. Delete/Backspace removes unlocked selected objects while the canvas has focus. Control+Z / Control+Y undo/redo; Control+S saves; Control+O opens. macOS also supports the equivalent Command shortcuts. Trackpad panning may require a mouse with a middle button.

## Drawing files

Save/Open use JSON in the `briancad-2` format with geometry, styles, layers, active layer, and grid preferences. Original `draft-prototype-1` JSON drawings still open and get a default layer. Save As creates a separate file; saves write a temporary file before replacing the destination. Unsaved changes trigger a discard prompt for New/Open/Exit. VC6 compatibility is outside this implementation.

## Validation

```bash
python3 src/check_geometry.py
python3 -m unittest discover -s src -p 'test_*.py' -v
python3 -m py_compile src/*.py
```

The suite includes geometry/construction, layer/history, legacy and new JSON, grid, and Tkinter workflow tests. Tkinter tests skip if `DISPLAY` is unset (except on macOS, where Tk uses the native display). They were exercised on a temporary Linux X display, including actual layer double-click events, Tab traversal, parameter edits, object dialogs, and save/reopen. Selection regressions additionally cover whole/partial windows, control deformations, immutable drag previews, snapping and final-release coordinates, cancellation, and one-step undo. Visual inspection covered the drawing window, layer/object dialogs, partial handle highlighting, and a live radius drag snapped to another circle quadrant. Native macOS testing is still needed.

Deferred tools include trim/extend, fillets, dimensions, text, nonuniform scaling, and printing to scale. Splines use explicitly documented interpolation/control algorithms; this is not a claim of exact historical Vellum spline behavior.
