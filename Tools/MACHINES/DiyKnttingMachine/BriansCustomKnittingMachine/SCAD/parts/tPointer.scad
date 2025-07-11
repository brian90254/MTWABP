include <../modules/camplate_coords_mk2.scad>;

tPointer();

module tPointer() {
    difference() {
    translate(tPointerCoord)
    linear_extrude(2)
    import("../../SVG/TPointer.svg");
    // TODO: this hole needs to match the one in tPivot so it should probably be extracted to a reusable module or something    
    translate(tPivotCoords)
    cylinder(camPlateHeight*4, d = screwDiamSm, center = true, $fn = 20);
    }
}