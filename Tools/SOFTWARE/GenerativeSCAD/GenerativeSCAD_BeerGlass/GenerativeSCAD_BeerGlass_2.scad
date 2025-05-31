$fn = 100; // Smooth curves

// Dimensions
glass_height = 203.2;
wall_thickness = 2.5;
rim_clearance = 0.2;

// Torus-style base ring
torus_major_radius = 30;     // horizontal distance from center
torus_minor_radius = 7;      // NEW minor radius
torus_vertical_offset = torus_minor_radius;  // OFFSET MOVED UP

// Outer glass profile
outer_profile = [
    [0, 0],
    [28, 0],
    [29, 20],
    [30, 60],
    [35, 130],
    [38, 160],
    [37, glass_height - 10],
    [38, glass_height],
    [0, glass_height]
];

// Inner profile (offset inward, raised bottom + rim)
inner_profile = [
    [0, glass_height + rim_clearance],
    [38 - wall_thickness, glass_height + rim_clearance],
    [37 - wall_thickness, glass_height - 10],
    [38 - wall_thickness, 160],
    [35 - wall_thickness, 130],
    [30 - wall_thickness, 60],
    [29 - wall_thickness, 20],
    [28 - wall_thickness, wall_thickness],
    [0, wall_thickness]
];

// Union: Glass body + Raised torus ring
union() {
    // Hollow glass
    difference() {
        color("blue")
        rotate_extrude()
            polygon(points=outer_profile);

        color("red")
        rotate_extrude()
            polygon(points=inner_profile);
    }

    // Torus ring, raised so it partially embeds in the base
    color("gray")
    translate([0, 0, torus_vertical_offset])
        rotate_extrude()
            translate([torus_major_radius, 0])
                circle(r=torus_minor_radius);
}
