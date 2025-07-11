include<../modules/params.scad>;

// fits over the tip of the eyebolt to secure the clamp to the table; captive ball pivots inside the cone shape so do not print with supports!

module clampHead() {
   $fn = 50;
   boltDiam = 7.8;
   
   // ball 
   difference() {
       sphere(d = boltDiam + 3);
       cylinder(h = boltDiam, d = boltDiam);
   }
   
   // socket
   difference() {
       translate([0,0,-(boltDiam) - tolerance *2]) 
       cylinder(h = boltDiam + 4, d1 = boltDiam * 4, d2 = boltDiam * 2);
       sphere(d = boltDiam + 3 + tolerance * 3);
   }
}

clampHead();