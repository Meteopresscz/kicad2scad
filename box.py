#!/usr/bin/env python3

import sys
import pcbnew
import matplotlib.pyplot as plt
import numpy as np
#from icecream import ic

MICRO = 0.000001

pcb = pcbnew.LoadBoard(sys.argv[1])

SCREW_HOLE_RADIUS = 1.2
SOLDER_BLOB_PADDING = 0.8

xx = []
yy = []
radiuses = []
padtypes = []
widths = []
heights = []

bbox = pcb.ComputeBoundingBox()
#ic(bbox.GetHeight())
#ic(bbox.GetOrigin())

#from IPython import embed; embed()

for pad in pcb.GetPads():
  description = pad.GetParent().GetDescription()
  if "SMD Solder Jumper" in description and pad.GetParent().GetLayerName() == "B.Cu":
    padtypes.append("jumper")
  elif pad.GetDrillSize()[0] == 0:
    padtypes.append("smd")
  elif "Mounting Hole" in description:
    if pad.GetDrillSize()[0] < 1000000:
      continue
    padtypes.append("hole")
  else:
    padtypes.append("tht")

  xx.append(pad.GetCenter()[0]*MICRO)
  yy.append(-pad.GetCenter()[1]*MICRO)
  radiuses.append(pad.GetBoundingRadius()*MICRO)

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

  colordict = {"smd":"gray", "tht":"green", "hole":"orange", "jumper": "red"}
  colors = [colordict[p] for p in padtypes]

  plt.scatter(xx,yy, s=sizes, c=colors)
  plt.show()


for x,y,radius,w,h,padtype in zip(xx,yy,radiuses,widths,heights,padtypes):

  if padtype == "smd":
    continue

  y_corrected = y-min(yy)

  if padtype == "hole":
    r = SCREW_HOLE_RADIUS
    z = -5
    print("translate([%f,%f,%f]) cylinder(r=%f,h=20);"%(x,y_corrected,z,r))
  else:
    color = ""
    if padtype == "jumper":
      color = "color([1,0,0]) "
    z = 5
    print(color + "translate([%f,%f,%f]) cube([%f,%f,5], center=true);"%(x,y_corrected,z,w+SOLDER_BLOB_PADDING,h+SOLDER_BLOB_PADDING))

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

