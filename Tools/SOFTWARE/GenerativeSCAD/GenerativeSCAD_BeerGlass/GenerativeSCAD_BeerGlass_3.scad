$fn = 100; // Smoothness

// Glass dimensions
glass_height = 203.2;
wall_thickness = 2.5;
rim_clearance = 0.2;

// Torus base ring dimensions
torus_major_radius = 26;     // slightly smaller due to narrow base
torus_minor_radius = 7;
torus_vertical_offset = torus_minor_radius;  // ring sits partly embedded

// Outer profile for Weizen glass (tall with narrow base and flared top)
outer_profile = [
    [0, 0],
    [24, 0],
    [25, 20],
    [24, 50],         // neck in
    [30, 100],        // bulge starts
    [36, 150],
    [38, glass_height],
    [0, glass_height]
];

// Inner profile (mirrors outer, inset by wall thickness, raised at base and top)
inner_profile = [
    [0, glass_height + rim_clearance],
    [38 - wall_thickness, glass_height + rim_clearance],
    [36 - wall_thickness, 150],
    [30 - wall_thickness, 100],
    [24 - wall_thickness, 50],
    [25 - wall_thickness, 20],
    [24 - wall_thickness, wall_thickness],
    [0, wall_thickness]
];

// Final model
union() {
    // Main glass
    difference() {
        color("blue")
        rotate_extrude()
            polygon(points=outer_profile);

        color("red")
        rotate_extrude()
            polygon(points=inner_profile);
    }

    // Torus-style base ring
    color("gray")
    translate([0, 0, torus_vertical_offset])
        rotate_extrude()
            translate([torus_major_radius, 0])
                circle(r=torus_minor_radius);
}
