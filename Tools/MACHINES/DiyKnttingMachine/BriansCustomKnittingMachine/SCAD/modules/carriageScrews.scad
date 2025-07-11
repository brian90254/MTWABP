include<params.scad>;

module carriageScrews() {
    
    // attach to back of camplate
    translate([screwHeadDiam*1.5,-6,camHeight + camPlateHeight/2]) 
    cylinder(h= 12*2, d = screwDiam, center = true);
    
    translate([CAM_PLATE_WIDTH/2,-6,camHeight + camPlateHeight/2]) 
    cylinder(h= 12*2, d = screwDiam, center = true);
    
    translate([CAM_PLATE_WIDTH - screwHeadDiam*1.5,-6,camHeight + camPlateHeight/2]) 
    cylinder(h= 12*2, d = screwDiam, center = true);

    // attach to front of camplate
    translate([screwHeadDiam*1.5,-(NEEDLE_BED_DEPTH - COMB - 6),camHeight + camPlateHeight/2]) 
    cylinder(h= 12*2, d = screwDiam, center = true);
    
    translate([CAM_PLATE_WIDTH/2,-(NEEDLE_BED_DEPTH - COMB - 6),camHeight + camPlateHeight/2]) 
    cylinder(h= 12*2, d = screwDiam, center = true);
    
    translate([CAM_PLATE_WIDTH - screwHeadDiam*1.5,-(NEEDLE_BED_DEPTH - COMB - 6),camHeight + camPlateHeight/2]) 
    cylinder(h= 12*2, d = screwDiam, center = true);
    
    // attach stripper plate 
    // this spot is tiny so we need to use smaller (#4) screws for this!
    translate([0,-(NEEDLE_BED_DEPTH + NEEDLE_EXTENSION + camPlateHeight - 0.25),0]) {
        // screw hole
        translate([0,0,2]) {
    
            translate([screwHeadDiamSm*1.5,0,0])
            cylinder(h= screwHeightSm, d = screwDiamSm, center = true);
            
            translate([screwHeadDiamSm*1.5 + 35,0,0])
            cylinder(h= screwHeightSm, d = screwDiamSm, center = true);
            
            translate([CAM_PLATE_WIDTH - screwHeadDiamSm*1.5 - 35,0,0])
            cylinder(h= screwHeightSm, d = screwDiamSm, center = true);
            
            translate([CAM_PLATE_WIDTH - screwHeadDiamSm*1.5,0,0])
            cylinder(h= screwHeightSm, d = screwDiamSm, center = true);
        
        }
        // countersink
        translate([0,0,6.5 + screwHeadHeight/2]) {
            
            translate([screwHeadDiamSm*1.5,0,0])
            cylinder(h= screwHeadHeightSm, d = screwHeadDiamSm, center = true);
 
            translate([screwHeadDiamSm*1.5 + 35,0,0])
            cylinder(h= screwHeadHeightSm, d = screwHeadDiamSm, center = true);

            translate([CAM_PLATE_WIDTH - screwHeadDiamSm*1.5 -35,0,0])
            cylinder(h= screwHeadHeightSm, d = screwHeadDiamSm, center = true);

            translate([CAM_PLATE_WIDTH - screwHeadDiamSm*1.5,0,0])
            cylinder(h= screwHeadHeightSm, d = screwHeadDiamSm, center = true);
        }
    }         
    
    // attach yarn feeder plate from underneath
    
    translate([0,-(NEEDLE_BED_DEPTH - COMB/2),0]) {
        
        translate([0,0,2 - tolerance]) {
            // screw holes
            translate([screwHeadDiam*1.5,0,0])
            cylinder(h= screwHeight-2, d = 2.8, center = false);
            
            translate([screwHeadDiam*1.5 + 35,0,0])
            cylinder(h= screwHeight-2, d = 2.8, center = false);
            
            translate([CAM_PLATE_WIDTH - screwHeadDiam*1.5 - 35,0,0])
            cylinder(h= screwHeight-2, d = 2.8, center = false);
            
            translate([CAM_PLATE_WIDTH - screwHeadDiam*1.5,0,0])
            cylinder(h= screwHeight-2, d = 2.8, center = false);
        
        
            // countersink
            translate([screwHeadDiam*1.5,0,0])
            cylinder(h= screwHeadHeight + tolerance, d = screwHeadDiam, center = false);
 
            translate([screwHeadDiam*1.5 + 35,0,0])
            cylinder(h= screwHeadHeight + tolerance, d = screwHeadDiam, center = false);

            translate([CAM_PLATE_WIDTH - screwHeadDiam*1.5 -35,0,0])
            cylinder(h= screwHeadHeight + tolerance, d = screwHeadDiam, center = false);

            translate([CAM_PLATE_WIDTH - screwHeadDiam*1.5,0,0])
            cylinder(h= screwHeadHeight + tolerance, d = screwHeadDiam, center = false);
        }
    }              
}