#!/usr/bin/env python3

import sys
import pcbnew
import matplotlib.pyplot as plt
import numpy as np
import argparse
#from icecream import ic

MICRO = 0.000001

parser = argparse.ArgumentParser(description="Convert THT components/pads in KiCad PCB to an OpenSCAD file.")
parser.add_argument("board_file", help="Path to the .kicad_pcb file")
parser.add_argument("--merge-distance", type=float, default=0.0, help="Distance (in mm) to consider pads for grouping.")
args = parser.parse_args()

pcb = pcbnew.LoadBoard(args.board_file)

SCREW_HOLE_RADIUS = 1.2
SOLDER_BLOB_PADDING = 1.1

xx = []
yy = []
radiuses = []
padtypes = []
comments = []
widths = []
heights = []

bbox = pcb.ComputeBoundingBox()
#ic(bbox.GetHeight())
#ic(bbox.GetOrigin())

for pad in pcb.GetPads():
  f = pad.GetParentFootprint()
  fp = f.GetFPID().GetUniStringLibId()
  description = f.GetLibDescription()

  value = f.GetFieldByName("Value").GetText()
  reference = f.GetFieldByName("Reference").GetText()
  comment = f"{reference}-{value}"

  if "SolderJumper" in description and pad.GetParent().GetLayerName() == "B.Cu":
    padtypes.append(["jumper"])
  elif "CON-SMA-EDGE-S" in description:
    padtypes.append(["sma"])
  elif pad.GetDrillSize()[0] == 0:
    padtypes.append(["smd"])
  elif "MountingHole" in description or "MountingHole" in value:

    appended = False

    if pad.GetDrillSize()[0] < 1000000: # footprints MountingHole_3.2mm_M3_Pad_Via would generate lots of small holes for the vias
      continue

    if description.startswith("Connector_Dsub") and pad.GetDrillSize()[0] <= 2000000: # Connector_Dsub:DSUB-9_Female_Horizontal_P2.77x2.84mm_EdgePinOffset4.94mm_Housed_MountingHolesOffset7.48mm
      padtypes.append(["tht", pad.GetDrillSize()[0]])
      appended = True

    #if pad.GetDrillSize()[0] > 3000000 and not appended:
    #  padtypes.append(["bighole", pad.GetDrillSize()[0]])
    #  appended = True

    if not appended:
      padtypes.append(["hole"])

  else:
    padtypes.append(["tht", pad.GetDrillSize()[0]])

  xx.append(pad.GetCenter()[0]*MICRO)
  yy.append(-pad.GetCenter()[1]*MICRO)
  radiuses.append(pad.GetBoundingRadius()*MICRO)
  comments.append(comment)

  #print(padtypes[-1], xx[-1], yy[-1], description, comment)

  widths.append(pad.GetBoundingBox().GetWidth()*MICRO)
  heights.append(pad.GetBoundingBox().GetHeight()*MICRO)


# edge
"""
for d in pcb.GetDrawings():
  #print(d.GetLayerName())
  if (d.GetLayerName() == 'F.Cu'):
    fcu = d
  if (d.GetLayerName() == 'Edge.Cuts'):
    fe = d
ex = fcu.GetCenter()[0]*MICRO
ey = -fcu.GetCenter()[1]*MICRO
ew = fe.GetBoundingBox().GetWidth()*MICRO
eh = fcu.GetBoundingBox().GetHeight()*MICRO
"""
#print(ew, eh)
#sys.exit(0)

if sys.stdout.isatty():
  sizes = (np.array(radiuses)*2)**2

  colordict = {"smd":"gray", "tht":"green", "hole":"orange", "jumper": "red", "sma": "blue"}
  colors = [colordict[p[0]] for p in padtypes]

  plt.scatter(xx,yy, s=sizes, c=colors)
  plt.show()

print("pad_z = 5;")
print("screw_z = -5;")

min_yy_val = min(yy)

# Add PCB outline cube
edge_bbox = pcb.GetBoardEdgesBoundingBox()

#from IPython import embed; embed()

if edge_bbox.IsValid():
    pcb_w = edge_bbox.GetWidth() * MICRO
    pcb_h = edge_bbox.GetHeight() * MICRO
    
    pcb_center_x_openscad = edge_bbox.GetCenter().x * MICRO
    pcb_center_y_openscad_inverted = -edge_bbox.GetCenter().y * MICRO
    
    pcb_center_y_final = pcb_center_y_openscad_inverted - min_yy_val
    
    print(f"// PCB Outline Cube")
    print(f"//% color([0,1,0,0.2]) translate([{pcb_center_x_openscad},{pcb_center_y_final},5]) cube([{pcb_w},{pcb_h},5], center=true);")
    print()

pads_to_process = []
holes_to_process = []

for x,y,radius,w,h,padtype,comment in zip(xx,yy,radiuses,widths,heights,padtypes,comments):

  if padtype[0] == "smd":
    continue

  y_corrected = y - min_yy_val

  if padtype[0] == "hole":
    holes_to_process.append({'x': x, 'y': y_corrected, 'comment': comment})
  elif padtype[0] in ["tht", "jumper", "sma"]:
    ww = w+SOLDER_BLOB_PADDING
    hh = h+SOLDER_BLOB_PADDING
    if padtype[0] == "sma":
      ww += 1
      hh += 1
    pads_to_process.append({
        'x': x, 'y': y_corrected, 'w': ww, 'h': hh,
        'comment': comment, 'type': padtype[0]
    })

# Print holes
for hole in holes_to_process:
    r = SCREW_HOLE_RADIUS
    print(f"translate([{hole['x']},{hole['y']},screw_z]) cylinder(r={r},h=20); // {hole['comment']}")

# Group and print THT-like pads
if args.merge_distance > 0:
    MERGE_DISTANCE = args.merge_distance # mm

    groups = []
    while pads_to_process:
        current_group = []
        queue = [pads_to_process.pop(0)]
        
        while queue:
            pad1 = queue.pop(0)
            current_group.append(pad1)
            
            remaining_pads = []
            for pad2 in pads_to_process:
                is_close = (abs(pad1['x'] - pad2['x']) * 2 < (pad1['w'] + pad2['w'] + MERGE_DISTANCE) and
                            abs(pad1['y'] - pad2['y']) * 2 < (pad1['h'] + pad2['h'] + MERGE_DISTANCE))
                
                if is_close:
                    queue.append(pad2)
                else:
                    remaining_pads.append(pad2)
            pads_to_process = remaining_pads
        groups.append(current_group)

    for group in groups:
        if not group:
            continue
        
        min_x = min(p['x'] - p['w']/2 for p in group)
        max_x = max(p['x'] + p['w']/2 for p in group)
        min_y = min(p['y'] - p['h']/2 for p in group)
        max_y = max(p['y'] + p['h']/2 for p in group)
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        total_w = max_x - min_x
        total_h = max_y - min_y
        
        comments = ", ".join(p['comment'] for p in group)
        
        color = ""
        if any(p['type'] == 'jumper' for p in group):
            color = "color([1,0,0]) "
            
        print(f"{color}translate([{center_x},{center_y},pad_z]) cube([{total_w},{total_h},5], center=true); // {comments}")
else:
    # Print individual pads without grouping
    for pad in pads_to_process:
        color = ""
        if pad['type'] == 'jumper':
            color = "color([1,0,0]) "
        print(f"{color}translate([{pad['x']},{pad['y']},pad_z]) cube([{pad['w']},{pad['h']},5], center=true); // {pad['comment']}")

