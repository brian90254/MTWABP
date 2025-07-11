include<../modules/params.scad>;
use<../parts/needleBed.scad>;
use<../parts/backCover.scad>;
use<../parts/spongeBar.scad>;
use<../modules/connector.scad>;

// TODO: needs refactoring!

clampWidth = 50;
clampDepth = NEEDLE_BED_DEPTH-clampWidth/2; 
clampThickness = 6;
clampHollow = 85; // adjust this for your table thickness

// LEFT
union() {
    translate([-gauge, 0, 0])
    carriageRest();
//    translate([-gauge/2,-connectorOffset,-needleBedHeight])
//    connector(tolerance = tolerance);
//    translate([-gauge/2,-(NEEDLE_BED_DEPTH-connectorOffset),-needleBedHeight])
//    connector(tolerance = tolerance);
}

//RIGHT
//difference() {
    translate([gauge*numNeedles, 0, 0])
    mirror([1,0,0])
    carriageRest();
//    translate([gauge*numNeedles - gauge/2 - tolerance,-connectorOffset,-needleBedHeight-tolerance])
//    connector();
//    translate([gauge*numNeedles - gauge/2 - tolerance,-(NEEDLE_BED_DEPTH-connectorOffset),-needleBedHeight - tolerance])
//    connector();
//}

////// CLAMP
translate([-gauge,0,0])
clampUnit();


module carriageRest() {
    union() {
        difference() {
            hull() {
                needleBase();   
                translate([-CAM_PLATE_WIDTH, -10, -needleBedHeight/2])
                cylinder(needleBedHeight, 10, 10, center = true); 
                
                translate([-CAM_PLATE_WIDTH, -NEEDLE_BED_DEPTH+10, -needleBedHeight/2])
                cylinder(needleBedHeight, 10, 10, center = true); 
            }
            for(i = [0:ceil(CAM_PLATE_WIDTH/gauge)]) {
               translate([-gauge*i, 0, 0])
               frontAngle(CAM_PLATE_WIDTH + 10);
            }
            // cutout for clamp
            translate([-CAM_PLATE_WIDTH/2, -NEEDLE_BED_DEPTH, -needleBedHeight])
                cube([clampWidth, clampDepth*2, clampThickness*2], center = true); 
            clampScrews();
        }
//        translate([gauge/2-CAM_PLATE_WIDTH/4,0,0]) {
//            frontRail(CAM_PLATE_WIDTH/2, rounded = true);
//            backRail(CAM_PLATE_WIDTH/2, rounded = true);
//        }
    }
}

module clampScrews() {
    // screwholes for clamp
    $fn = 50;
    translate([-CAM_PLATE_WIDTH/2,0,-needleBedHeight]) {
        translate([0,-(NEEDLE_BED_DEPTH-clampWidth),0]) {
            translate([- clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ - clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
        }
        translate([0,-clampWidth*2/3,0]) {
            translate([- clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ - clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
        }
    }
}

module clampUnit() {
    difference() {
        // top
        translate([-CAM_PLATE_WIDTH/2 , -NEEDLE_BED_DEPTH + clampDepth/2, -needleBedHeight + clampThickness/2])
            cube([clampWidth - tolerance*2, clampDepth - tolerance, clampThickness-tolerance], center = true); 
        clampScrews();
        for(i = [0:ceil(CAM_PLATE_WIDTH/gauge)]) {
           translate([-gauge*i, 0, 0])
           frontAngle(CAM_PLATE_WIDTH + 10);
        }
    }
    // front
    hull () {
        translate([-CAM_PLATE_WIDTH/2 , -NEEDLE_BED_DEPTH + clampThickness/2 + 12, -(needleBedHeight - tolerance) - clampHollow/2]) {
                cube([clampWidth - tolerance*2, clampThickness, clampHollow], center = true);
            
            // rounded edge
            translate([0,0,-(clampHollow + clampThickness)/2])
            rotate([0,90,0])
            cylinder(clampWidth - tolerance*2, d = clampThickness, center = true, $fn = 30);
        }  
    }
    difference() {
        // bottom
        translate([-CAM_PLATE_WIDTH/2 , -NEEDLE_BED_DEPTH + clampDepth/2 +  clampThickness/2, -(needleBedHeight - tolerance) - clampHollow - clampThickness/2 ])
        cube([clampWidth - tolerance*2, clampDepth - 25, clampThickness], center = true);
        
        
        translate([-CAM_PLATE_WIDTH/2,-clampWidth*2/3 - 18,-(needleBedHeight - tolerance) - clampHollow - clampThickness/2]) {
            // bolt hole
            cylinder(h = clampThickness*2, d = 8, center = true, $fn = 50);
            
            // nut cutout
            translate([-14.491/2,-12.55/2,clampThickness/2]) // use w/h specs from svg
            #linear_extrude(6.75, center = true)
            import("../../SVG/HexNut.svg");
        }        
    }
}

