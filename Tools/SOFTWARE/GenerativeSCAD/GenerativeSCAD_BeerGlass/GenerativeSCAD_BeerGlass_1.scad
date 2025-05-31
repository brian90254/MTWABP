$fn = 100; // Curve resolution

// Dimensions
glass_height = 203.2;      // 8 inches
wall_thickness = 2;        // mm
rim_clearance = 0.2;       // upward offset to avoid rim artifacts

// Outer profile (blue)
outer_profile = [
    [0, 0],
    [30, 0],
    [32, 40],
    [35, glass_height - 20],
    [40, glass_height],
    [0, glass_height]
];

// Inner profile (red, offset inward & raised at top; base starts at wall_thickness height)
inner_profile = [
    [0, glass_height + rim_clearance],
    [40 - wall_thickness, glass_height + rim_clearance],
    [35 - wall_thickness, glass_height - 20],
    [32 - wall_thickness, 40],
    [30 - wall_thickness, wall_thickness],
    [0, wall_thickness]
];

// Final model with colored difference
difference() {
    // Outer shell
    color("blue")
    rotate_extrude()
        polygon(points=outer_profile);

    // Inner cavity
    color("red")
    rotate_extrude()
        polygon(points=inner_profile);
}
