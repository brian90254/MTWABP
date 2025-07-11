include<../modules/params.scad>;
include<../modules/camplate_coords_mk2.scad>;
include<../modules/utils.scad>;
use<../parts/backCover.scad>;
use<../parts/spongeBar.scad>;
include<../parts/tPointer.scad>;
include<../modules/carriageScrews.scad>;
use<../parts/tCam.scad>;
include<../parts/backPlate.scad>;


/* 
Full camplate assembly for layout and debugging
See individual files to export models
*/


// --- LAYOUT: CAMS ---

translate(tCamCoords)
tCam();
translate(flip(tCamCoords))
mirror([1,0,0])
tCam();

translate(tPivotCoords)
tPivot(solid = true);
translate(flip(tPivotCoords))
mirror([1,0,0])
tPivot(solid = true); 
