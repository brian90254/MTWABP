# A 3D-printable flatbed knitting machine

## Contents
[Before you start](#before-you-start)

[How to use this code](#how-to-use-this-code)

[How to build the machine](#how-to-build-the-machine)

[Basic use and tips](#basic-use)

[Table of 3D printed parts and slicer settings](#3d-printed-parts-and-slicer-settings)

## Before you start

If you are interested in the background, motivations, research, and design process for this project, and especially if you'd like to contribute, please check out the [video series](https://www.youtube.com/playlist?list=PLWDnfcUpk7PLQRvfuGytMauK_sR6CEwI9).

Please keep in mind that this is a passion project and a work-in-progress, not a finished product. You may find bugs or imperfections and if you do I hope you will report them, kindly and patiently. This machine probably won't do everything you could possibly want a knitting machine to do; I am open to hearing your cool feature ideas but I can't promise if or when I'll implement them. 

**IMPORTANT: knitting machine needles are not all interchangeable**, and this machine has been designed to work with a specific model: when sourcing your needles please look for those intended to work with Brother models KR830 / KR838 / KR850.  

## How to use this code

In this project, you will find several types of file:

1. In the **STL** directory you can find pre-compiled models of parts with the default settings, ready to be sliced for 3D printing. If you're not interested in customizing or tinkering and just want to start printing parts, open this folder and skip to the next section, [How to build the machine](#how-to-build-the-machine).

1. The **SCAD** directory contains the modelling code, which can be viewed and edited in [OpenSCAD](https://openscad.org/). This code is divided into:
    - **parts** files, each of which can render and export a single component (or in some cases, pairs of components which are meant to be printed together);
    - **assemblies**, which help visualize how the components will fit together; and
    - **modules**, utility code and parameters which are shared across multiple parts and assemblies.

        - If you want or need to make changes, the key parameters are in **modules/params.scad**. Values that are open to tweaking are named in ```camelCase```; for example, you may want to change the number of needles in a bed, set a custom spacing between needles, adjust the size of screw holes, or fine-tune the tolerances. (Note that you will also need to open individual parts files to view and export your updated models after saving the changes in **params.scad**.) However, you should avoid changing values marked as constants in ```SCREAMING_SNAKE_CASE```. These are carefully calibrated to the needle dimensions and should generally not be changed without also adjusting the cam design and associated SVG assets to compensate. I DO NOT recommend you make changes to the cam layout unless you are very familiar with the project and committed to doing A LOT of testing.

1. The **SVG** directory contains 2D shape assets exported from the technical drawings, which are imported by the SCAD files and extruded into 3D parts such as cams, etc. You shouldn't need to access or modify these files directly.

1. The **Technical Sketches** directory contains design drawings which can be opened in Adobe Illustrator; these can be used to inspect the cam layout, obtain precise measurements and coordinates, and export SVG assets. These are provided for reference, I DO NOT recommend you make changes to the cam layout unless you are very familiar with the project and committed to doing A LOT of testing.

## How to build the machine

[A video demonstration is also available](https://youtu.be/eFesPhYR8KI).

### Printing and supplies

A table of printable parts along with suggested slicer settings can be found below, based on my own tests slicing in Cura and printing with PLA/PLA Pro filament on an Ender 3 V2; note that times and filament weights given are estimates and your experience may vary depending on your printer and slicer. A list of other required hardware, supplies and tools is also provided below.

The needlebed in the provided STL files holds 25 needles at a standard (4.5mm) gauge; if you want a bed with a different number or spacing of needles, these parameters can be changed in **SCAD/modules/params.scad**; you will then need to export the updated models from **needlebed.scad**, **backCover.scad**, and **spongeBar.scad** in **SCAD/parts/**. Multiple needlebeds can be connected in series to create a wider work area. 

**Please note** that knitting machine needles are not all interchangeable, and this machine has been designed to work with a specific model: when sourcing your needles please look for those intended to work with Brother models KR830 / KR838 / KR850.

I recommend sourcing all your hardware before printing your parts.

### Assembling the needlebeds

You will need to print:

- left and right carriage rests
- 2x carriage rest clamp
- 2x clamp head
- 2x clamp bolt (omit if using metal clamp hardware, see note)
- 2x clamp nut (omit if using metal clamp hardware, see note)
- one or more needlebeds (I recommend starting with one and testing before printing additional bed)
- one back cover per needlebed
- one sponge bar per needlebed

You will also need:

- latch-hook knitting machine needles (KR830 / KR838 / KR850), one per  needlebed slot for each bed
- self-adhesive foam weatherstrip (or similar; for sponge bar), 1/4" - 3/8" wide, enough length to span all connected needlebeds, plus a small trimming allowance
- round head machine screws: 
    * #4-40 x 1/2", 4 per needlebed (for back cover)
    * #4-40 x 3/4", 2 per needlebed (for sponge bar)
    * #6-32 x 1/2", 8 (for carriage rests/clamps)
- screwdriver
- scissors or utility knife (to cut foam weatherstrip)
- NOTE: I have been using a 5/16" x 3.5" metal eyebolt in the clamp; the eye is easy to grab and turn without a tool, but not essential. You will need a longer bolt if you choose the "deep" clamp option. If you choose to generate 3D printed bolts for your clamp with an external library, a bolt with an 8mm OD and 12mm nut (between flats) should fit the other connected parts.

For each needlebed:

1. Insert a needle into each slot with the hook end towards the angled edge of the bed; ensure needles are sliding smoothly (sand any imperfections if necessary).
2. Screw back cover to rear of needlebed with #4-40 x 1/2" screws (in any orientation; it's symmetrical). Ensure screw heads are sunk in the well below the surface of the cover but be careful not to overtighten.
3. Cut and apply foam strip to fit the flat underside of the sponge bar; make a cut through the foam strip at the position of each screw hole for the screw to pass through.
4. Screw sponge bar into place with #4-40 x 3/4" screws, taking care that the foam strip doesn't get caught between the spacer and the cover; once in place, the sponge bar should be flush with the surface of the rest of the needlebed. Once again, ensure the screw heads do not protrude, but avoid overtightening.

For each carriage rest:

1. Remove 3D printing supports, sanding any resulting rough surfaces if needed. 
2. Screw the clamp to the bottom of the carriage rest with #6-32 x 1/2" screws, ensuring that the surfaces are flush.
3. Insert the clamp nut into the hexagonal cutout in the clamp, and the bolt from the opposite side; once the bolt has cleared the nut, insert the tip of the bolt into the clamp head, and (when all beds are connected) tighten to the table. (You may choose to glue or otherwise permanently affix the nut and the clamp head; I keep mine separate since they are a tight fit around my table.)

To connect the carriage rests and beds:
1. Slide the slots on the left-hand edge of the unit over the pegs on the right-hand edge of its neighbour. 
2. Repeat until the desired number of beds have been connected and add the right carriage rest.

### Assembling the MkII carriage

You will need to print:

- back plate
- 2x tension cams, mirrored
- 2x tension pointers
- yarn carrier
- yarn feeder 
- stripper plate (2pc.)
- round head machine screws:
    * 4x #6-32 x 1/2"
    * 6x #4-40 x 1/2"
    * 6x #4-40 x 1/4"
    * 2x #4-40 nuts
    * 2x #4 washers

You will also need:
- pliable jewelry wire, approx. 6-7" (15-18cm)
- sandpaper
- screwdriver
- pliers
- side cutters/nippers (if cutting the wire)
- safety goggles (if cutting the wire)


1. Remove any 3D printing supports and sand any resulting rough surfaces, if needed. 
2. For each tension cam: with the flat side of the back plate down, insert the tension cam's pivot point into the hole; the nut side of the cam will be against the plate in the region of the arc-shaped cutout. Holding the cam in place, flip the assembly over (flat side facing you) and screw the round end of a tension pointer to the underside of the cam pivot, with a #4-40 x 1/4" screw. Insert a washer between the pointer and the plate, and connect the pointer, washer, plate and tension cam with a #4-40 x 1/2" screw.
3. With the angled face of the yarn carrier cover facing down and the cone-shaped side of the yarn feeder facing up, screw the two parts together using #4-40 x 1/4" screws. Flip the yarn carrier assembly over and align the stripper plate pieces under the opposite edge, so that the points of the stripper plate form a small gap under the yarn feeder hole; screw into place with #4-40 x 1/2" screws. 
12. With the flat side of the camplate facing up, align the yarn carrier assembly with the screw holes at the front edge of the camplate (closest to the hold position). Screw into place with #6-32 screws.
13. Create a yarn guide with the jewelry wire by coiling around a small cylinder 3 times; form one end of the coil into a small loop (or otherwise finish the cut edge according to your preference). Form the other end into a flat loop or coil, and wrap around a #6-32 screw; secure the yarn guide with the screw in the middle hole at the back of the carriage, and bend into your preferred position to guide the yarn towards the yarn feeder.

## Basic use

Machine knitting is a skilled craft that takes time and patience to learn. If you've never knit by machine before, be prepared to spend some (maybe a lot of) time practicing techniques. 

A full introduction to machine knitting is beyond the scope of this guide, but there are many approachable lessons elsewhere online; for the most relevant information to this style of machine, I recommend looking for techniques demonstrated on simple, single-bed machines such as the Bond Ultimate Sweater Machine (there are a few differences between those machines and this one but they have a lot of the basics in common). 

Instead, this overview will focus on the peculiarities of this machine and the essentials you'll need to get set up.

### Yarn

This machine uses needles which can knit a range of yarn from ultrafine lace or fingering weights (on the 4.5mm gauge bed) to some lighter worsted weights (on every-other needle or on a 9mm gauge bed), but in my experience the heavier side of that range has behaved unpredictably. Beginners may reduce frustration by looking for smooth, consistent wool or quality acrylic yarns in fingering, sport, or DK weight (best on a 6.5mm bed) for their first projects; avoid bulky or heavily textured "art" yarns, slippery fibers, or very inelastic cotton yarns, at least until you are comfortable with the machine. Yarns must be wound into a ball/cake which feeds smoothly from the centre.

### Weight

Weight must be applied to the knitting as it is created in order to maintain the proper tension and help pull the old stitches over the new ones. I use a weighted hem/cast-on rag with a built-in pocket or channel to hold a metal rod or bar, but you could also use a cast-on rag with claw weights if you already have them. For my weighted hem, I use a flat (rather than tubular) version of the cast-on bonnet with split rings in this [Dean & Bean tutorial](https://www.deanandbean.com/setup-bonnet-pattern-20), but there are many other options to get started: the key features are pre-existing loops to hang onto your needles, and something to attach your weight to so that it is distributed evenly across the width of your project. Experiment with different amounts of weight (you might need more than you expect!) and keep in mind that different projects might require different amounts of weight, too.

Problems that might occur due to insufficient weight include: dropped stitches, unintentional tucked stitches, split stitches.

### Casting on

Push the desired number of needles into a working position (tips of hooks at or just past the edge of the bed). Hang a loop from your cast-on rag/hem onto (at least) every other needle, then add your weights. 

Set the carriage onto the carriage rest, aligning the needlebed's rails with the corresponding channels in the underside of the carriage; the stripper plate will hook under the angled front edge of the needledbed. 

Before knitting with your project yarn, establish several rows of "waste" yarn (this can be reused many times, so it doesn't really need to go to waste). Set the yarn into the carriage by feeding it through the wire coil, over the top of the carriage, and into the slot in the yarn feeder's funnel. Pass the yarn through the gap in the stripper plate and lay it over the stripper plate, away from the direction of knitting. Pull some slack in the yarn out of the ball so that it will feed freely when the carriage is moved.

Ensure the latches of all the working needles are open so that they can receive yarn as the carriage passes over them. Using gentle downward pressure, slide the carriage towards the needles, starting slowly to watch that the first needle catches the yarn; you may need to hold the loose end of the yarn to add a little bit of tension as these first few stitches form. Continue sliding the carriage across the needlebed until all working needles have been cleared. 

Check that new stitches have been formed successfully through every loop and that every needle now holds yarn. If not, you can correct the missed stitches manually (for a few misses) or remove the knitting and rehang the cast-on rag and start again again (for a lot). If stitches are consistently not forming correctly, double-check that: 
- all latches are open
- enough weight has been added
- yarn is feeding through the wire coil guide and into the feeder.

Between rows, pull more yarn out of the ball if necessary so that it will feed freely. Gently tension the yarn with one hand as you slide the carriage back towards the first needle, removing any excessive slack from the yarn feeder so that the loop formed around the first needle is snug, then drop the yarn and let it feed freely once the first couple of stitches have formed.

Once you have established a few rows of waste yarn and stitches are consistently knitting correctly, you can switch to project yarn and cast on using whatever technique is called for in your pattern. For ease of removal later, I recommend separating the waste yarn from the project yarn with a single row of "ravel cord": a thin, smooth, contrasting colour yarn which will easily slide out when pulled, allowing the adjoining pieces to pull apart without cutting the waste yarn.

### Carriage settings and needle positions

Tension can be adjusted by loosening the screws at the sharp end of the tension pointers and pivoting the tension cams to a new position; re-tighten the screws to set the new tension. Pointers set more towards the top edge of the carriage will loosen the tension, while settings towards the side edge of the carriage will tighten the tension. 

Needles with butts aligned all the way to the back of the bed are **out of work**; these needles will not be actuated by any cams in any setting, will not form stitches, and should not hold any yarn. Latches should be closed before placing needles in this position.

The "home" position for needles exiting the carriage is the standard **working position**. Between the working position and the hold position is the **forward working position**, at the point where latches have just pushed forward past the old loop on the needle. With the MkII carriage, needles in both these positions will always knit. The forward working position can be used when returning needles to work from the hold position or other manipulations that leave the live stitch behind the latch. If the stitches are behind the latches in this position, it is important to ensure latches are open before knitting the next row, otherwise the hook will not be able to catch a new loop of yarn before the old loop is dropped.

Needles with their butts aligned all the way to the front of their slots are in **hold position**. These needles will not be actuated and will not knit but can hold live stitches, which is useful for tuck stitches and short rows. Because the stitches are behind the latches in this position, it is particularly important to ensure latches are open before returning the needles to work, or the hook will not be able to catch a new loop of yarn before the old loop is dropped.

### Troubleshooting

As mentioned above, common causes of issues include insufficient weight, improperly closed latches, or yarn not having been properly fed into the yarn guide and yarn feeder; these can cause dropped stitches, skipped/tucked stitches, or split stitches.

Other issues may include:

#### Tension problems

Generally poor tension that can't be fixed within the available range of the tension cams or by changing to a different gauge of needlebed could be a problem if the yarn you have chosen is inappropriate, for example, too thick or too textured for one stitch to pull smoothly through another. Previously good tension can be suddenly affected if the yarn is not flowing freely out of the ball, if it catches on another object, if it gets knotted, or if it gets wrapped around the yarn coil; to correct these problems, pause and check for impediments before re-knitting any problem stitches if necessary.

#### Carriage jams

Sometimes the carriage may jam due to one of its edges catching on part of the needlebed, usually where a connection between two beds is not completely flush; in this case, the jam can usually be cleared by gently lifting the leading edge of the carriage 1-2mm and gently sliding forward. Check that your work surface is flat and smooth, that there are no unexpected objects under any part of the bed, and that your beds haven't warped or deformed.

In some cases the cause of a jam is a needle which has hit an unexpected obstacle due to being out of position: for example, if a needle which should be out of work has slipped forward slightly. Needles can also jam due to tension problems, knots in the yarn, or malformed stitches, which can all prevent needles from actuating through their full range.

Sometimes these needle jams may occur while the needle is underneath the carriage, in which case it is difficult to see the source of the problem. If you can't see or reach the needle to diagnose the problem, I recommend removing the carriage: lift the carriage off the rails, tilt forward to clear the needles, and set aside. Unknit any worked stitches from the unsuccessful pass and reset to start the row again.

Regardless of the cause of the jam, it is important to stop moving the carriage. DO NOT try to push through sudden, unexpected resistance. Sometimes a needle jam can be cleared by *gently* wiggling the carriage back and forth by a centimetre or two, but attempting to force it may damage your machine.

#### Maintenance and storage conditions

Some plastics used for 3D printing are more vulnerable to heat than others. When not in use, store your knitting machine components in dry conditions, at room temperature, and out of direct sunlight. Do not leave the parts in a hot car or near other sources of heat.

Parts which contact the needles, especially the cams, may benefit from a wax or plastic-friendly lubricant in between projects.

When storing the needlebeds, be cautious of the needle hooks and latches; they can be damaged if they get caught on foreign objects or otherwise treated roughly.


## 3D printed parts and slicer settings

|Part              |#  |Mirroring  |Orientation              |Layer height          |Supports?                  |Infill|Z-seam alignment|Initial layer horizontal expansion  |Print time (est.)|Weight (est., g)|Metres (est.)|
|------------------|---|-----------|-------------------------|----------------------|---------------------------|------|----------------|------------------------------------|-----------------|----------------|-------------|
|backPlate         |1  |n/a        |Flat top aligned to plate|.2mm / adaptive layers|None                       |20%   |Sharpest corner |-0.1mm to -0.2mm                    |12h33            |119             |39.93        |
|tCam              |2  |Mirror one |Hex nut up               |.2mm                  |Normal, touching buildplate|100%  |Sharpest corner |-0.1mm to -0.2mm                    |TBC              |TBC             |TBC          |
|stripperPlate     |1  |None       |Lay flat                 |.2mm / adaptive layers|None                       |100%  |Sharpest corner |-0.1mm to -0.2mm                    |5h42             |35              |11.84        |
|Yarn feeder       |1  |n/a        |Lay flat                 |.12mm / adaptive      |None                       |20%   |Default         |-0.1mm to -0.2mm                    |4h02             |25              |8.49         |
|Yarn carrier cover|1  |n/a        |Lay flat                 |.2mm                  |Below overhang             |20%   |Default         |-0.1mm to -0.2mm                    |6h57             |                |             |
|Needlebed         |1  |n/a        |Lay flat                 |.2mm                  |None                       |15%   |Sharpest corner |-0.1mm to -0.2mm                    |14h12            |111             |37.35        |
|Back cover *      |1  |n/a        |Lay flat                 |.2mm                  |None                       |20%   |Sharpest corner |-0.1mm to -0.2mm                    |2h53             |23              |7.57         |
|Sponge cover *    |1  |n/a        |Lay flat                 |.2mm                  |None                       |20%   |Sharpest corner |-0.1mm to -0.2mm                    |see backCover    |see backCover   |see backCover|
|Carriage rest L   |1  |n/a        |TBC                      |TBC                   |TBC                        |TBC   |TBC             |TBC                                 |TBC              |TBC             |TBC          |
|Carriage rest R   |1  |n/a        |TBC                      |TBC                   |TBC                        |TBC   |TBC             |TBC                                 |TBC              |TBC             |TBC          |
|Clamps            |2  |TBC        |TBC                      |TBC                   |TBC                        |TBC   |TBC             |TBC                                 |TBC              |TBC             |TBC          |
|Clamp heads       |2  |TBC        |TBC                      |TBC                   |TBC                        |TBC   |TBC             |TBC                                 |TBC              |TBC             |TBC          |

\* Back cover and sponge bar were sliced and printed in the same job; a combined time/weight estimate is provided
