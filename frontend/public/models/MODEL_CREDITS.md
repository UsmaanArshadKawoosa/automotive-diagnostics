# 3D Model Credits and Licenses

This document lists all 3D models used in the Automotive AI Diagnostic Engine project, their sources, and licensing information.

## CarConcept (Detailed Sedan Model)

**Source:** KhronosGroup glTF-Sample-Assets  
**Repository:** https://github.com/KhronosGroup/glTF-Sample-Assets  
**Model Path:** Models/CarConcept  
**File:** sedan_detailed.glb (downloaded from glTF-Binary/CarConcept.glb)

**Created by:** DGG (Darmstadt Graphics Group GmbH)  
**Original Model:** Public domain 3D model created by Unity Fan  
**Optimized by:** DGG using RapidPipeline tools  
**Contributed to:** KhronosGroup glTF-Sample-Assets

**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**License URL:** https://creativecommons.org/licenses/by/4.0/

**Attribution Required:**
```
KhronosGroup glTF-Sample-Assets
CarConcept by DGG
CC BY 4.0
```

**Original Asset License Notes:**
- The asset was started from a public domain 3D model created by Unity Fan
- Then optimized and converted into a well-formed glTF asset
- Showcases high graphical quality in glTF while maintaining small download size
- Includes KHR_materials_variants for material switching

**File Size:** ~11.8 MB (11,778,688 bytes)

---

## Kenney Car Kit (Fallback Models)

**Source:** Kenney Assets  
**Repository:** https://kenney.nl/assets/car-kit  
**Itch.io:** https://kenney-assets.itch.io/car-kit

**Models Used:**
- hatchback.glb (hatchback-sports.glb from Kenney)
- sedan.glb (sedan.glb from Kenney)
- suv.glb (suv.glb from Kenney)
- pickup.glb (truck.glb from Kenney)
- van.glb (van.glb from Kenney)

**License:** Creative Commons Zero (CC0) / Public Domain  
**License URL:** https://creativecommons.org/publicdomain/zero/1.0/

**Attribution:** Not required, but crediting Kenney is appreciated:
```
Kenney Assets (kenney.nl)
Car Kit by Kenney
CC0 / Public Domain
```

**Original License Notes:**
- Content may be used for personal, educational, and commercial purposes
- Attribution is not required but appreciated
- Includes 40+ models in OBJ, FBX, and glTF formats

**File Sizes:**
- hatchback.glb: ~198 KB
- sedan.glb: ~172 KB
- suv.glb: ~208 KB
- pickup.glb: ~176 KB
- van.glb: ~176 KB

---

## Summary

| Vehicle Type | Primary Model | Fallback Model |
|--------------|---------------|----------------|
| Sedan | CarConcept (sedan_detailed.glb) - CC BY 4.0 | Kenney sedan.glb - CC0 |
| Hatchback | Kenney hatchback.glb - CC0 | Procedural |
| SUV | Kenney suv.glb - CC0 | Procedural |
| Pickup | Kenney pickup.glb - CC0 | Procedural |
| Van | Kenney van.glb - CC0 | Procedural |

The procedural generic vehicle model serves as the ultimate fallback when all GLB assets fail to load or when WebGL is unavailable.