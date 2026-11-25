
 · MD
<div align="center">
# MEKELLE UNIVERSITY
## MEKELLE INSTITUTE OF TECHNOLOGY
 
**Course Title:** Artificial Intelligence (AI)
 
**Project Title:**
### Real-World Problem Solving via BFS and DFS
 
</div>
---
 
## Group Members Information
 
| No. | Group Member Name | Student ID |
|:---:|-------------------|------------|
| 1 | Abel Adhanom | MIT/UR187791/16 |
| 2 | Fikadu Gebremedhin | MIT/UR188115/16 |
| 3 | Selemun Welegebrial | MIT/UR188651/16 |
| 4 | Mulugeta Teamrat | MIT/UR190604/16 |
| 5 | Tsegay Araya | MIT/UR188761/16 |
| 6 | Gebrekiros Gebrezgiher | MIT/UR190719 |
 
**Submitted to:** Mr. Wudasie Gereziher
**Submission Date:** 27 November 2026
 
---
 
# MIT Campus Navigator (BFS & DFS)
 
A small AI-course project that solves a real-world problem - **finding your way around the
Mekelle Institute of Technology campus** - with graph search.
 
| Algorithm | What it does here |
|-----------|-------------------|
| **BFS** | Finds the **shortest route** (fewest steps) between two campus locations. |
| **DFS** | **Explores** the campus from a start location, going as deep as possible before backtracking. |
 
The campus is a graph: 7 locations (nodes) and 8 connections (edges), drawn on a satellite map.
 
## Run
 
```bash
pip install -r requirements.txt 
python main.py
```
 
Keep `main.py` and `campus_map.png` in the same folder.
 
## Using the app
 
1. Choose **From** and **To** (or press **Swap**).
2. **Shortest route · BFS** draws the route in green with numbered steps.
3. **Explore campus · DFS** draws the exploration tree in amber with the visiting order.
4. **Connections** lists who is linked to whom. **Reset** clears the map.
## Files
 
| File | Purpose |
|------|---------|
| `main.py` | Graph, BFS, DFS, map renderer and the Tkinter window |
| `campus_map.png` | Clean map (574 x 836) - cropped from `img_1.png`, Google Maps buttons removed |
| `prep_map.py` | One-off script that made `campus_map.png` (optional) |
| `img_1.png` | Original screenshot |
 
## Moving a node
 
Run `python main.py --coords` and click the spot on the map: the map pixel is printed in the
terminal. Put it in `NODE_POSITIONS` at the top of `main.py`.
 
## Notes
 
- Map imagery: Google Maps (the attribution stays visible on the map).
- The window is DPI-aware, so it stays sharp on Windows laptops with 125% / 150% display scaling.
