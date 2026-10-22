# Draft: first 2D workflow prototype

An independent, Vellum-inspired desktop drafting prototype for Linux. This is a first interaction model, not a complete CAD system or a verified reproduction of Vellum's exact behavior. It includes original Python code only; no Vellum binaries or assets are bundled.

## Start on Linux Mint

Install Python and its standard GUI package if needed:

    sudo apt install python3 python3-tk

From this project folder, run the current source:

    python3 src/draft.py

The ZIP in this folder is the original milestone snapshot; use `src/` for the current implementation.

No pip packages are needed.

## Try the known drawing

Click **Load 2-inch line / 1-inch circle** to create a green horizontal line from (-1, 0) to (1, 0) and a blue circle centered at (0, 0), diameter 1 inch. This generates known geometry; it does not import the VC6 sample.

## Tools

- **Line:** click a start point, then an endpoint. Enable Connected lines for a chain.
- **Circle:** click a center, then a point on its circumference.
- **Select:** click close to the outline of an object. Gold handles mark selection.
- **Move:** select an object first, switch to Move, then click a reference point and its destination. Or enter X/Y displacement and Apply exact entry.
- **Exact entry:** with Line selected, X/Y specifies the start, Length specifies length, and Angle is measured counterclockwise from positive X. With Circle selected, X/Y specifies the center and Diameter specifies diameter. Exact entry creates a complete object independently of a pending mouse operation. Decimal inches only.
- **Snapping:** endpoints, line midpoints, circle centers and quadrants, and the origin. A second line point can align horizontally, vertically, or along either 45° diagonal through its start. The same alignment applies to mouse-based moves. The visual snap tolerance stays at 9 screen pixels while zooming.
- Wheel zooms around the pointer. Middle-button drag pans. Fit frames all geometry.
- Escape cancels a pending operation. Delete removes the selection when the drawing canvas has keyboard focus. Ctrl+Z/Ctrl+Y undo/redo. Ctrl+S saves.

Drawings save as readable JSON in this prototype's own format. Open accepts this format only. Unsaved changes trigger a discard prompt when opening, starting a new drawing, loading the demo, or exiting.

## Grid preferences

Click **Grid preferences…** to open the Grid dialog. **Grid spacing (inches)** sets the major interval (default 1 inch); **# of subdivisions** divides that interval into equal parts (default 4, giving 1/4-inch minor spacing). One subdivision displays major lines only. Decimal values and simple fractions such as `1/2` are accepted for spacing. Cancel leaves the current values unchanged.

Major lines are darker than minor lines and both remain anchored at the origin. Zooming does not change their spacing. Lines closer than 8 screen pixels are hidden to avoid an unreadable dense grid; the status bar indicates this. Snapping continues to use the configured minor spacing, including hidden lines.

**Snap to grid** is independent of **Show grid** and **Object snaps / alignment**. It snaps to vertical or horizontal grid lines, grid intersections, and intersections of existing finite line segments with either major or minor grid lines. It does not extend segments or intersect circles with the grid. Grid preferences and checkbox states apply for the current application session; they are not saved in drawing JSON.

Snap priority within the 9-pixel tolerance is: object anchors, line/grid intersections, grid intersections, angular alignment, then individual grid lines. Each tier chooses its nearest candidate. Thus an existing endpoint remains usable even if it is slightly off-grid. Grid-line snaps preserve the other coordinate instead of forcing every point onto a grid intersection. Angular guides include all eight directions in 45° increments. Turn off Snap to grid when you want angular alignment to take precedence over nearby grid intersections; exact numeric entry remains exact regardless of snap settings.

## Current scope

Implemented: lines, circles, single-object selection/move/delete, numeric entry, basic snaps and alignment, pen colors, configurable major/minor grid and grid snapping, 45° alignment, zoom/pan, undo/redo, and JSON save/load.

Future: arcs, trim/extend, offsets, fillets, splines, dimensions, layers, multi-selection, copy/rotate/mirror, intersection/tangent/perpendicular snapping, and printing to scale. There is no VC6 support. Alignment is currently to the active start point, not arbitrary inferred guides. Moving shows start-point guides but no moving-object preview.

## Validation

Run `python3 src/check_geometry.py` for headless geometry and editor-state checks. These cover the supplied example dimensions, hit testing, snapping, exact line entry, coordinate transforms, move, undo/redo, and JSON validation. Python compilation also passed. The build environment had no graphical display, so window rendering and mouse/keyboard interaction have not been exercised visually; test those on your Linux machine before using this for real design work.

Run `python3 -m unittest discover -s src -p test_grid.py -v` for grid preferences, segment/grid intersections, snap priorities and tolerances, dense grids, and all eight angular alignment directions.
