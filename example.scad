$fn=32;

module hld() {
  difference() {
    hull() {
      translate([5,0,-1]) cylinder(d=10, h=2);
      translate([155,0,-1]) cylinder(d=10, h=2);
    }
    translate([5,0,-5]) cylinder(d=4.2, h=10);
    translate([155,0,-5]) cylinder(d=4.2, h=10);
  }
}

difference() {

  union() {

    // Example flaps for screws
    for(i=[0:50:200]) {
      translate([0,2+i,0]) hld();
    }

    // The main holder body
    translate([10,-3,-1]) cube([140,225,4]);
  }

  // Our board output
  %translate([59,1,-2.75]) rotate([0,0,0]) {include <diff.scad>};

  // Example cutout
  translate([9,12,-0.5]) cube([33,25.5,4]);
}
