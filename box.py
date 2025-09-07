#!/usr/bin/env python3

import sys
import pcbnew
import matplotlib.pyplot as plt
import numpy as np
#from icecream import ic

MICRO = 0.000001

if len(sys.argv) < 2:
  print("Convert THT components/pads in KiCad PCB to an OpenSCAD file.")
  print("Usage: %s <board.kicad.pcb>"%sys.argv[0])
  sys.exit(2)

pcb = pcbnew.LoadBoard(sys.argv[1])

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
    print(f"% color([0,1,0,0.2]) translate([{pcb_center_x_openscad},{pcb_center_y_final},5]) cube([{pcb_w},{pcb_h},5], center=true);")
    print()

for x,y,radius,w,h,padtype,comment in zip(xx,yy,radiuses,widths,heights,padtypes,comments):

  if padtype[0] == "smd":
    continue

  y_corrected = y - min_yy_val

  if padtype[0] == "hole":
    r = SCREW_HOLE_RADIUS
    print("translate([%f,%f,screw_z]) cylinder(r=%f,h=20);"%(x,y_corrected,r), end="")
  else:
    color = ""
    if padtype[0] == "jumper":
      color = "color([1,0,0]) "

    ww = w+SOLDER_BLOB_PADDING
    hh = h+SOLDER_BLOB_PADDING
    if padtype[0] == "sma":
      ww += 1
      hh += 1
    print(color + "translate([%f,%f,pad_z]) cube([%f,%f,5], center=true);"%(x,y_corrected,ww,hh), end="")
  print(f" // {comment}")

"""
bbox = pcb.GetBoard().GetBoundingBox()
print("%%translate([%f,%f,4]) cube([%f,%f,10], center=true);"%(
  bbox.GetCenter()[0]*MICRO,
  bbox.GetCenter()[1]*MICRO,
  bbox.GetWidth()*MICRO,
  bbox.GetHeight()*MICRO
))
"""

"""
print("%%translate([%f,%f,4]) cube([%f,%f,10], center=true);"%(
  ex, ey, eh, ew
))
"""

