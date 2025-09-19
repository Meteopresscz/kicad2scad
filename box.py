#!/usr/bin/env python3

import sys
import pcbnew
import matplotlib.pyplot as plt
import numpy as np
import argparse
#from icecream import ic

MICRO = 0.000001

def board_to_pads_and_holes(board_file):
    pcb = pcbnew.LoadBoard(board_file)

    pads_data = []

    for pad in pcb.GetPads():
      f = pad.GetParentFootprint()
      description = f.GetLibDescription()

      value = f.GetFieldByName("Value").GetText()
      reference = f.GetFieldByName("Reference").GetText()
      comment = f"{reference}-{value}"

      pad_info = {
          'x': pad.GetCenter()[0] * MICRO,
          'y': -pad.GetCenter()[1] * MICRO,
          'radius': pad.GetBoundingRadius() * MICRO,
          'width': pad.GetBoundingBox().GetWidth() * MICRO,
          'height': pad.GetBoundingBox().GetHeight() * MICRO,
          'comment': comment,
      }

      padtype = []
      if "SolderJumper" in description and pad.GetParent().GetLayerName() == "B.Cu":
        padtype.append("jumper")
      elif "CON-SMA-EDGE-S" in description:
        padtype.append("sma")
      elif pad.GetDrillSize()[0] == 0:
        padtype.append("smd")
      elif "MountingHole" in description or "MountingHole" in value:

        if pad.GetDrillSize()[0] < 1000000: # footprints MountingHole_3.2mm_M3_Pad_Via would generate lots of small holes for the vias
          continue

        appended = False
        if description.startswith("Connector_Dsub") and pad.GetDrillSize()[0] <= 2000000: # Connector_Dsub:DSUB-9_Female_Horizontal_P2.77x2.84mm_EdgePinOffset4.94mm_Housed_MountingHolesOffset7.48mm
          padtype.extend(["tht", pad.GetDrillSize()[0]])
          appended = True

        if not appended:
          padtype.append("hole")

      else:
        padtype.extend(["tht", pad.GetDrillSize()[0]])

      if not padtype:
          continue

      pad_info['padtype'] = padtype
      pads_data.append(pad_info)


    edge_bbox = pcb.GetBoardEdgesBoundingBox()
    board_outline = None
    if edge_bbox.IsValid():
        x_offset = edge_bbox.GetX() * MICRO
        y_offset = -edge_bbox.GetBottom() * MICRO
        pcb_w = edge_bbox.GetWidth() * MICRO
        pcb_h = edge_bbox.GetHeight() * MICRO
        board_outline = {'w': pcb_w, 'h': pcb_h}
    else:
        # Fallback to bounding box of all pads
        if pads_data:
            x_offset = min(p['x'] for p in pads_data)
            y_offset = min(p['y'] for p in pads_data)
        else:
            x_offset = 0
            y_offset = 0

    for pad in pads_data:
        pad['x'] -= x_offset
        pad['y'] -= y_offset

    return pads_data, board_outline

parser = argparse.ArgumentParser(description="Convert THT components/pads in KiCad PCB to an OpenSCAD file.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("board_files", nargs='+', help="Path to one or more .kicad_pcb files")
parser.add_argument("--merge-distance", type=float, default=0.0, help="Distance (in mm) to consider pads for grouping.")
parser.add_argument("--board-outline", action="store_true", help="Include PCB outline in the output.")
parser.add_argument("--grouping-method", choices=['rectangle', 'hull'], default='hull', help="Method for grouping pads ('rectangle' or 'hull').")
args = parser.parse_args()

all_pads_data = []
all_board_outlines = []

for board_file in args.board_files:
    pads_data, board_outline_data = board_to_pads_and_holes(board_file)

    if board_outline_data:
        all_board_outlines.append(board_outline_data)

    all_pads_data.extend(pads_data)

param_comment = f"// Generated with command: {' '.join(sys.argv)}"
print(param_comment)

SCREW_HOLE_RADIUS = 1.2
SOLDER_BLOB_PADDING = 1.1

if sys.stdout.isatty():
  xx = [p['x'] for p in all_pads_data]
  yy = [p['y'] for p in all_pads_data]
  radiuses = [p['radius'] for p in all_pads_data]
  padtypes = [p['padtype'] for p in all_pads_data]
  sizes = (np.array(radiuses)*2)**2

  colordict = {"smd":"gray", "tht":"green", "hole":"orange", "jumper": "red", "sma": "blue"}
  colors = [colordict[p[0]] for p in padtypes]

  plt.scatter(xx,yy, s=sizes, c=colors)
  plt.show()

print("pad_z = 5;")
print("screw_z = -5;")

#from IPython import embed; embed()

if all_board_outlines:
    comment = ""
    if not args.board_outline:
       comment = "//"

    print(f"// PCB Outline Cube")
    for board_outline in all_board_outlines:
        pcb_w = board_outline['w']
        pcb_h = board_outline['h']
        
        pcb_center_x_final = pcb_w / 2
        pcb_center_y_final = pcb_h / 2
        
        print(f"{comment}% color([0,1,0,0.2]) translate([{pcb_center_x_final},{pcb_center_y_final},5]) cube([{pcb_w},{pcb_h},5], center=true);")
    print()

pads_to_process = []
holes_to_process = []

for pad in all_pads_data:
  padtype = pad['padtype']

  if padtype[0] == "smd":
    continue

  if padtype[0] == "hole":
    holes_to_process.append({'x': pad['x'], 'y': pad['y'], 'comment': pad['comment']})
  elif padtype[0] in ["tht", "jumper", "sma"]:
    ww = pad['width']+SOLDER_BLOB_PADDING
    hh = pad['height']+SOLDER_BLOB_PADDING
    if padtype[0] == "sma":
      ww += 1
      hh += 1
    pads_to_process.append({
        'x': pad['x'], 'y': pad['y'], 'w': ww, 'h': hh,
        'comment': pad['comment'], 'type': padtype[0]
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
        
        comments = ", ".join(p['comment'] for p in group)
        
        color = ""
        if any(p['type'] == 'jumper' for p in group):
            color = "color([1,0,0]) "
        
        if len(group) > 1:
            if args.grouping_method == 'hull':
                print(f"{color}hull() {{ // {comments}")
                for pad in group:
                    print(f"  translate([{pad['x']},{pad['y']},pad_z]) cube([{pad['w']},{pad['h']},5], center=true); // {pad['comment']}")
                print(f"}}")
            else: # rectangle
                min_x = min(p['x'] - p['w']/2 for p in group)
                max_x = max(p['x'] + p['w']/2 for p in group)
                min_y = min(p['y'] - p['h']/2 for p in group)
                max_y = max(p['y'] + p['h']/2 for p in group)
                
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                total_w = max_x - min_x
                total_h = max_y - min_y
                
                print(f"{color}translate([{center_x},{center_y},pad_z]) cube([{total_w},{total_h},5], center=true); // {comments}")
        elif group:
            pad = group[0]
            print(f"{color}translate([{pad['x']},{pad['y']},pad_z]) cube([{pad['w']},{pad['h']},5], center=true); // {comments}")
else:
    # Print individual pads without grouping
    for pad in pads_to_process:
        color = ""
        if pad['type'] == 'jumper':
            color = "color([1,0,0]) "
        print(f"{color}translate([{pad['x']},{pad['y']},pad_z]) cube([{pad['w']},{pad['h']},5], center=true); // {pad['comment']}")

