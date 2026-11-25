"""
MIT Campus Navigator
====================
Graph search on the MIT campus map:
  * BFS - shortest route (fewest steps) between two locations
  * DFS - order in which the campus is explored from a start location

Run:   python main.py
Needs: Pillow  (pip install -r requirements.txt) and campus_map.png next to this file.
Tip:   python main.py --coords   prints the map pixel under every click, handy for moving nodes.
"""

import math
import sys
import tkinter as tk
from collections import deque
from functools import lru_cache
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageTk

# Crisp (not blurry) UI on Windows screens that use 125% / 150% scaling.
if sys.platform == "win32":
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. Campus graph
# ---------------------------------------------------------------------------
MAP_FILE = Path(__file__).resolve().parent / "campus_map.png"

MIT_CAMPUS = {
    "MIT Main Academic Area": [
        "Central Road Junction",
        "Eastern Building Area",
        "Northern Road Junction",
    ],
    "MIT Dormitory": ["Northern Road Junction"],
    "Class Rooms": ["Central Road Junction"],
    "Central Road Junction": [
        "MIT Main Academic Area",
        "Class Rooms",
        "Southern Building Area",
        "Eastern Building Area",
    ],
    "Eastern Building Area": [
        "MIT Main Academic Area",
        "Central Road Junction",
        "Southern Building Area",
    ],
    "Southern Building Area": ["Central Road Junction", "Eastern Building Area"],
    "Northern Road Junction": ["MIT Dormitory", "MIT Main Academic Area"],
}

# Pixel position of every node on campus_map.png (574 x 836).
NODE_POSITIONS = {
    "MIT Main Academic Area": (182, 388),
    "MIT Dormitory": (412, 98),
    "Class Rooms": (88, 779),
    "Central Road Junction": (214, 468),
    "Eastern Building Area": (302, 436),
    "Southern Building Area": (322, 686),
    "Northern Road Junction": (267, 286),
    "foot-ball field": (200, 250),
}

# Preferred side of each name tag (default: right); it moves automatically if that spot is taken.
LABEL_SIDE = {"Central Road Junction": "left", "Southern Building Area": "below"}

# Every undirected connection once.
EDGES = sorted({tuple(sorted((a, b))) for a, nbrs in MIT_CAMPUS.items() for b in nbrs})

# ---------------------------------------------------------------------------
# 2. Search algorithms
# ---------------------------------------------------------------------------


def bfs(graph, start, goal):
    """Shortest path (fewest edges) from start to goal, or None."""
    queue, seen = deque([[start]]), {start}
    while queue:
        path = queue.popleft()
        if path[-1] == goal:
            return path
        for nxt in graph[path[-1]]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(path + [nxt])
    return None


def dfs(graph, start):
    """Depth-first walk. Returns (visit_order, tree_edges) with tree_edges = [(parent, child), ...]."""
    order, edges, seen = [], [], set()

    def explore(node, parent=None):
        seen.add(node)
        order.append(node)
        if parent:
            edges.append((parent, node))
        for nxt in graph[node]:
            if nxt not in seen:
                explore(nxt, node)

    explore(start)
    return order, edges


# ---------------------------------------------------------------------------
# 3. Map renderer (Pillow, anti-aliased) - no Tk inside, so it is easy to test
# ---------------------------------------------------------------------------
BG, CARD, BORDER = "#f1f5f9", "#ffffff", "#dbe3ec"
MAP_BG, NAVY = "#e2e8f0", "#0f172a"
TEXT, MUTED = "#0f172a", "#64748b"
BLUE, GREEN, AMBER = "#2563eb", "#16a34a", "#f59e0b"
SS = 3  # supersampling: draw 3x bigger, shrink down -> smooth lines and text


@lru_cache(maxsize=16)
def _font(size):
    for name in (
        "segoeuib.ttf",
        "arialbd.ttf",
        "Arial Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)  # Pillow >= 10.1


class MapRenderer:
    MAX_ZOOM, MARGIN = 1.6, 14

    def __init__(self, path, ui_scale=1.0):
        self.base = Image.open(path).convert("RGB")
        self.k = ui_scale
        self.view = (0, 0, 1.0)  # (x_offset, y_offset, scale) of the last render
        self._cache = (None, None)

    def _scaled_base(self, size):
        if self._cache[0] != size:
            img = self.base.resize(size, Image.Resampling.LANCZOS)
            img = Image.blend(
                img, Image.new("RGB", size, "black"), 0.12
            )  # slight dim so overlays pop
            self._cache = (size, img)
        return self._cache[1]

    def render(self, width, height, route=(), dfs_order=(), dfs_edges=()):
        """Return a width x height RGB image: the map centred, with the current overlay drawn on it."""
        k, m = self.k, int(self.MARGIN * self.k)
        bw, bh = self.base.size
        s = min((width - 2 * m) / bw, (height - 2 * m) / bh, self.MAX_ZOOM)
        iw, ih = max(1, int(bw * s)), max(1, int(bh * s))
        ox, oy = (width - iw) // 2, (height - ih) // 2
        self.view = (ox, oy, s)

        def u(v):  # UI pixels -> supersampled pixels
            return v * k * SS

        def pt(name):
            x, y = NODE_POSITIONS[name]
            return x * s * SS, y * s * SS

        layer = Image.new("RGBA", (iw * SS, ih * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        active = bool(route or dfs_order)

        # -- connections -----------------------------------------------------
        alpha = 95 if active else 215
        for a, b in EDGES:
            d.line([pt(a), pt(b)], fill=(15, 23, 42, alpha // 2), width=int(u(4.5)))
            d.line([pt(a), pt(b)], fill=(255, 255, 255, alpha), width=int(u(2)))

        # -- BFS route / DFS tree --------------------------------------------
        def tri(tip, ux, uy, size, fill):
            left = (
                tip[0] - ux * size - uy * size * 0.7,
                tip[1] - uy * size + ux * size * 0.7,
            )
            right = (
                tip[0] - ux * size + uy * size * 0.7,
                tip[1] - uy * size - ux * size * 0.7,
            )
            d.polygon([tip, left, right], fill=fill)

        def draw_links(pairs, colour):
            for a, b in pairs:  # white halo first so overlapping segments stay clean
                d.line([pt(a), pt(b)], fill=(255, 255, 255, 240), width=int(u(11)))
            for a, b in pairs:
                d.line([pt(a), pt(b)], fill=colour, width=int(u(6.5)))
            for a, b in pairs:  # arrow head near the target node
                (x1, y1), (x2, y2) = pt(a), pt(b)
                dist = math.hypot(x2 - x1, y2 - y1)
                if not dist:
                    continue
                ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
                back = min(u(30), dist * 0.5)
                tip = (x2 - ux * back, y2 - uy * back)
                tri(
                    (tip[0] + ux * u(3), tip[1] + uy * u(3)),
                    ux,
                    uy,
                    u(19),
                    (255, 255, 255, 255),
                )
                tri(tip, ux, uy, u(15), colour)

        numbers, colour = {}, None
        if route:
            numbers, colour = (
                {n: i for i, n in enumerate(route, 1)},
                ImageColor.getrgb(GREEN) + (255,),
            )
            draw_links(list(zip(route, route[1:])), colour)
        elif dfs_order:
            numbers, colour = (
                {n: i for i, n in enumerate(dfs_order, 1)},
                ImageColor.getrgb(AMBER) + (255,),
            )
            draw_links(dfs_edges, colour)

        # -- nodes -----------------------------------------------------------
        blue = ImageColor.getrgb(BLUE) + (255,)
        for name in NODE_POSITIONS:
            x, y = pt(name)
            if name in numbers:
                r = u(13)
                d.ellipse(
                    [x - r - u(3), y - r, x + r + u(3), y + r + u(6)],
                    fill=(0, 0, 0, 60),
                )
                d.ellipse(
                    [x - r - u(2.5), y - r - u(2.5), x + r + u(2.5), y + r + u(2.5)],
                    fill="white",
                )
                d.ellipse([x - r, y - r, x + r, y + r], fill=colour)
                d.text(
                    (x, y),
                    str(numbers[name]),
                    font=_font(int(u(13))),
                    fill="white",
                    anchor="mm",
                )
            else:
                r = u(7)
                d.ellipse(
                    [x - r - u(3), y - r - u(1.5), x + r + u(3), y + r + u(4.5)],
                    fill=(0, 0, 0, 60),
                )
                d.ellipse(
                    [x - r - u(3), y - r - u(3), x + r + u(3), y + r + u(3)],
                    fill="white",
                )
                d.ellipse([x - r, y - r, x + r, y + r], fill=blue)

        # -- name tags: each takes the first free spot (no overlap with other tags or dots) --
        font = _font(int(u(14)))
        pad_x, pad_y, gap, edge = u(9), u(5.5), u(17), u(6)
        dots = {n: pt(n) for n in NODE_POSITIONS}
        placed = []

        def free(box, own):
            x0, y0, x1, y1 = box
            if (
                x0 < edge
                or y0 < edge
                or x1 > layer.width - edge
                or y1 > layer.height - edge
            ):
                return False
            if any(x0 < q[2] and x1 > q[0] and y0 < q[3] and y1 > q[1] for q in placed):
                return False
            r = u(13)
            return not any(
                x0 - r < px < x1 + r and y0 - r < py < y1 + r
                for n, (px, py) in dots.items()
                if n != own
            )

        for name, (x, y) in dots.items():
            l, t, r_, b = d.textbbox((0, 0), name, font=font)
            w, h = r_ - l + 2 * pad_x, b - t + 2 * pad_y
            spots = {
                "right": (x + gap, y - h / 2),
                "left": (x - gap - w, y - h / 2),
                "below": (x - w / 2, y + gap),
                "above": (x - w / 2, y - gap - h),
            }
            first = LABEL_SIDE.get(name, "right")
            box = None
            for side in [first] + [k_ for k_ in spots if k_ != first]:
                bx, by = spots[side]
                if free((bx, by, bx + w, by + h), name):
                    box = (bx, by, bx + w, by + h)
                    break
            if box is None:  # crowded: use the preferred spot, kept inside the map
                bx, by = spots[first]
                bx = min(max(bx, edge), layer.width - w - edge)
                by = min(max(by, edge), layer.height - h - edge)
                box = (bx, by, bx + w, by + h)
            placed.append(box)
            d.rounded_rectangle(box, radius=h / 2, fill=(15, 23, 42, 215))
            d.text(
                (box[0] + pad_x - l, box[1] + pad_y - t), name, font=font, fill="white"
            )

        # -- compose: shrink overlay, add to map, round the corners ----------------
        frame = self._scaled_base((iw, ih)).convert("RGBA")
        frame.alpha_composite(layer.resize((iw, ih), Image.Resampling.LANCZOS))
        mask = Image.new("L", (iw * SS, ih * SS), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, iw * SS - 1, ih * SS - 1], radius=u(14), fill=255
        )
        out = Image.new("RGB", (width, height), MAP_BG)
        out.paste(
            frame.convert("RGB"),
            (ox, oy),
            mask.resize((iw, ih), Image.Resampling.LANCZOS),
        )
        return out


# ---------------------------------------------------------------------------
# 4. Application window
# ---------------------------------------------------------------------------
FONT = "Segoe UI"


def F(size, weight="normal"):
    return (FONT, size, weight)


class CampusApp:
    def __init__(self, root):
        self.root = root
        self.k = max(1.0, round(root.winfo_fpixels("1i") / 96, 2))  # UI scale (DPI)
        self.renderer = MapRenderer(MAP_FILE, self.k)
        self.route, self.dfs_order, self.dfs_edges = [], [], []
        self._job = self._img_id = self.photo = None

        root.title("MIT Campus Navigator")
        root.configure(bg=BG)
        sw, sh, k = root.winfo_screenwidth(), root.winfo_screenheight(), self.k
        w, h = min(int(1180 * k), sw - 60), min(int(740 * k), sh - 100)
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 2 - 20)}")
        root.minsize(min(int(960 * k), w), min(int(580 * k), h))

        self._style()
        self._build()
        self._show_welcome()
        if "--coords" in sys.argv:
            self.canvas.bind("<Button-1>", self._print_coords)

    # -- styling ------------------------------------------------------------
    def _style(self):
        k = self.k
        s = ttk.Style(self.root)
        s.theme_use("clam")
        self.root.option_add("*TCombobox*Listbox.font", F(10))
        s.configure(
            "TCombobox",
            fieldbackground=CARD,
            background=CARD,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            arrowsize=int(15 * k),
            padding=int(6 * k),
        )
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", CARD)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", CARD)],
            selectforeground=[("readonly", TEXT)],
            bordercolor=[("focus", BLUE)],
        )
        s.configure(
            "Vertical.TScrollbar",
            background=BORDER,
            troughcolor=CARD,
            bordercolor=CARD,
            arrowcolor=MUTED,
            relief="flat",
        )

        def button(name, bg, fg, hover, border=None, pad=(12, 9), size=10):
            s.configure(
                name,
                background=bg,
                foreground=fg,
                font=F(size, "bold"),
                borderwidth=1,
                bordercolor=border or bg,
                lightcolor=bg,
                darkcolor=bg,
                focuscolor=bg,
                relief="flat",
                padding=(int(pad[0] * k), int(pad[1] * k)),
            )
            s.map(name, background=[("active", hover), ("pressed", hover)])

        button("Green.TButton", GREEN, "white", "#15803d")
        button("Amber.TButton", AMBER, "#1f2937", "#d97706")
        button(
            "Ghost.TButton",
            "#f1f5f9",
            TEXT,
            "#e2e8f0",
            border=BORDER,
            pad=(10, 7),
            size=9,
        )

    # -- layout ---------------------------------------------------------------
    def _card(self, parent):
        return tk.Frame(
            parent,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=int(16 * self.k),
            pady=int(14 * self.k),
        )

    def _build(self):
        k = self.k
        header = tk.Frame(self.root, bg=NAVY, padx=int(22 * k), pady=int(10 * k))
        header.pack(fill="x")
        tk.Label(
            header, text="MIT Campus Navigator", font=F(16, "bold"), bg=NAVY, fg="white"
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Mekelle Institute of Technology  ·  BFS & DFS graph search",
            font=F(9),
            bg=NAVY,
            fg="#94a3b8",
        ).pack(anchor="w")

        body = tk.Frame(self.root, bg=BG, padx=int(16 * k), pady=int(16 * k))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        # map
        mapbox = tk.Frame(body, bg=MAP_BG)
        mapbox.grid(row=0, column=0, sticky="nsew")
        self.canvas = tk.Canvas(mapbox, bg=MAP_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        # side panel
        panel = tk.Frame(body, bg=BG, width=int(460 * k))
        panel.grid(row=0, column=1, sticky="ns", padx=(int(16 * k), 0))
        panel.pack_propagate(False)

        locations = list(MIT_CAMPUS)
        self.start_var = tk.StringVar(value="MIT Dormitory")
        self.dest_var = tk.StringVar(value="Class Rooms")

        card = self._card(panel)
        card.pack(fill="x")
        head = tk.Frame(card, bg=CARD)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text="Plan a route", font=F(12, "bold"), bg=CARD, fg=TEXT).pack(
            side="left"
        )
        ttk.Button(head, text="Swap", style="Ghost.TButton", command=self._swap).pack(
            side="right"
        )
        for caption, var in (("FROM", self.start_var), ("TO", self.dest_var)):
            tk.Label(card, text=caption, font=F(8, "bold"), bg=CARD, fg=MUTED).pack(
                anchor="w"
            )
            ttk.Combobox(
                card, textvariable=var, values=locations, state="readonly", font=F(10)
            ).pack(fill="x", pady=(2, 10))
        ttk.Button(
            card,
            text="Shortest route  ·  BFS",
            style="Green.TButton",
            command=self._run_bfs,
        ).pack(fill="x", pady=(4, 6))
        ttk.Button(
            card,
            text="Explore campus  ·  DFS",
            style="Amber.TButton",
            command=self._run_dfs,
        ).pack(fill="x")
        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", pady=(8, 0))
        row.columnconfigure((0, 1), weight=1, uniform="a")
        ttk.Button(
            row,
            text="Connections",
            style="Ghost.TButton",
            command=self._show_connections,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(row, text="Reset", style="Ghost.TButton", command=self._reset).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        res = self._card(panel)
        res.pack(fill="both", expand=True, pady=(int(12 * k), 0))
        self.res_title = tk.Label(res, anchor="w", font=F(12, "bold"), bg=CARD)
        self.res_title.pack(fill="x")
        self.res_sub = tk.Label(res, anchor="w", font=F(9), bg=CARD, fg=MUTED)
        self.res_sub.pack(fill="x", pady=(0, 6))

        box = tk.Frame(res, bg=CARD)
        box.pack(fill="both", expand=True)
        bar = ttk.Scrollbar(box, orient="vertical")
        self.out = tk.Text(
            box,
            height=4,
            wrap="word",
            relief="flat",
            bg=CARD,
            fg=TEXT,
            font=F(10),
            padx=0,
            pady=0,
            spacing1=3,
            spacing3=3,
            cursor="arrow",
            highlightthickness=0,
            state="disabled",
            yscrollcommand=bar.set,
        )
        bar.config(command=self.out.yview)
        bar.pack(side="right", fill="y")
        self.out.pack(side="left", fill="both", expand=True)
        self.out.tag_configure("body", font=F(10))
        self.out.tag_configure("num", font=F(10, "bold"))
        self.out.tag_configure("head", font=F(10, "bold"), spacing1=int(8 * k))
        self.out.tag_configure("muted", foreground=MUTED)

        legend = tk.Frame(res, bg=CARD)
        legend.pack(fill="x", pady=(8, 0))
        for colour, label in (
            (BLUE, "Location"),
            (GREEN, "BFS route"),
            (AMBER, "DFS order"),
        ):
            tk.Label(legend, text="●", fg=colour, bg=CARD, font=F(10)).pack(side="left")
            tk.Label(legend, text=label, fg=MUTED, bg=CARD, font=F(9)).pack(
                side="left", padx=(2, 12)
            )

    # -- map drawing ------------------------------------------------------------
    def _on_resize(self, _event):
        if self._job:
            self.root.after_cancel(self._job)
        self._job = self.root.after(
            40, self._redraw
        )  # redraw once the resizing settles

    def _redraw(self):
        self._job = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 50 or h < 50:
            return
        img = self.renderer.render(w, h, self.route, self.dfs_order, self.dfs_edges)
        self.photo = ImageTk.PhotoImage(img)
        if self._img_id:
            self.canvas.itemconfig(self._img_id, image=self.photo)
        else:
            self._img_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

    def _print_coords(self, event):
        ox, oy, s = self.renderer.view
        x, y = round((event.x - ox) / s), round((event.y - oy) / s)
        if 0 <= x < self.renderer.base.width and 0 <= y < self.renderer.base.height:
            print(f"({x}, {y})")

    # -- result panel -------------------------------------------------------------
    def _show(self, title, subtitle, colour, blocks):
        self.res_title.config(text=title, fg=colour)
        self.res_sub.config(text=subtitle)
        self.out.config(state="normal")
        self.out.delete("1.0", "end")
        self.out.tag_configure("num", foreground=colour)
        for tag, text in blocks:
            self.out.insert("end", text, tag)
        self.out.config(state="disabled")
        self.out.yview_moveto(0)

    def _show_welcome(self):
        self._show(
            "How it works",
            f"{len(MIT_CAMPUS)} locations  ·  {len(EDGES)} connections",
            TEXT,
            [
                ("head", "BFS - shortest route\n"),
                (
                    "body",
                    "Spreads out level by level, so the first route it reaches the destination "
                    "uses the fewest steps.\n",
                ),
                ("head", "DFS - exploration\n"),
                (
                    "body",
                    "Follows one branch as deep as it can, then backtracks. Numbers on the map "
                    "show the visiting order.\n",
                ),
            ],
        )

    # -- actions ---------------------------------------------------------------------
    def _swap(self):
        a, b = self.start_var.get(), self.dest_var.get()
        self.start_var.set(b)
        self.dest_var.set(a)

    def _clear(self):
        self.route, self.dfs_order, self.dfs_edges = [], [], []

    def _run_bfs(self):
        start, goal = self.start_var.get(), self.dest_var.get()
        self._clear()
        if start == goal:
            self._redraw()
            self._show(
                "Same location",
                "Pick a different destination.",
                MUTED,
                [("body", "You are already at " + start + ".")],
            )
            return
        path = bfs(MIT_CAMPUS, start, goal)
        self.route = path or []
        self._redraw()
        if not path:
            self._show(
                "No route found",
                f"{start} to {goal}",
                MUTED,
                [("body", "These locations are not connected.")],
            )
            return
        blocks = []
        for i, name in enumerate(path, 1):
            blocks += [("num", f"{i:>2}   "), ("body", name + "\n")]
        self._show(
            "Shortest route (BFS)",
            f"{len(path) - 1} steps  ·  {len(path)} locations",
            GREEN,
            blocks,
        )

    def _run_dfs(self):
        start = self.start_var.get()
        order, edges = dfs(MIT_CAMPUS, start)
        self._clear()
        self.dfs_order, self.dfs_edges = order, edges
        self._redraw()
        blocks = []
        for i, name in enumerate(order, 1):
            blocks += [("num", f"{i:>2}   "), ("body", name + "\n")]
        self._show(
            "Campus exploration (DFS)",
            f"Started at {start}  ·  {len(order)} locations",
            "#d97706",
            blocks,
        )

    def _show_connections(self):
        blocks = []
        for name, nbrs in MIT_CAMPUS.items():
            blocks.append(("head", name + "\n"))
            for nb in nbrs:
                blocks += [("muted", "     →  "), ("body", nb + "\n")]
        self._show("Campus connections", "Who is directly linked to whom", BLUE, blocks)

    def _reset(self):
        self._clear()
        self._redraw()
        self._show_welcome()


def main():
    if not MAP_FILE.exists():
        tk.Tk().withdraw()
        messagebox.showerror(
            "Map not found", f"Put {MAP_FILE.name} in the same folder as main.py."
        )
        return
    root = tk.Tk()
    CampusApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
