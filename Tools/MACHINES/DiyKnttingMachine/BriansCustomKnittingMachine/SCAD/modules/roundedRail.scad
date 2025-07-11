include<params.scad>;

module roundedRail(width,depth,height) {
    $fn = 30;
    rad = depth/2;
    translate([-width/2,0,0])
    hull() {
        translate([width/2,0,0])
        cube([width-rad*3,depth,height], center = true);
        translate([rad, 0, height/2 - rad]) {
            sphere(rad);
            translate([0,0,-height/2 + 0.5])
            cylinder(1,rad,rad, center = true);
        }
        translate([width - rad,0,0])
        {
            sphere(rad);
            translate([0,0,-height/2 + 0.5])
            cylinder(1,rad,rad, center = true);
        }
    }
}