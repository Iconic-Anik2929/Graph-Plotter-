import tkinter as tk
from tkinter import ttk, messagebox
import math

# ---- Safe namespace for eval() -------------------------------------------
SAFE_NAMES = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}


# Reciprocal trig functions (not in the math module by default)
def cot(x):
    return 1.0 / math.tan(x)


def sec(x):
    return 1.0 / math.cos(x)


def csc(x):
    return 1.0 / math.sin(x)


# Inverse reciprocal trig functions
def acot(x):
    if x == 0:
        return math.pi / 2
    return math.atan(1.0 / x)


def asec(x):
    return math.acos(1.0 / x)


def acsc(x):
    return math.asin(1.0 / x)


SAFE_NAMES.update({
    "abs": abs, "pow": pow, "min": min, "max": max,
    "cot": cot, "sec": sec, "csc": csc,
    "acot": acot, "asec": asec, "acsc": acsc,
})

COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
          "#46f0f0", "#f032e6", "#9a6324", "#008080"]

TRIG_FUNCS = ["sin(x)", "cos(x)", "tan(x)", "cot(x)", "sec(x)", "csc(x)"]
INV_TRIG_FUNCS = ["asin(x)", "acos(x)", "atan(x)", "acot(x)", "asec(x)", "acsc(x)"]


class GraphPlotter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ISHA's Graph Plotter")
        self.geometry("1000x700")
        self.minsize(760, 550)

        self.x_min, self.x_max = -10.0, 10.0
        self.y_min, self.y_max = -10.0, 10.0

        self._drag_start = None
        self._build_ui()
        self._plot()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = ttk.Frame(self, padding=(8, 8, 8, 4))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="f(x) =").pack(side=tk.LEFT)
        self.expr_var = tk.StringVar(value="x**2")
        entry = ttk.Entry(top, textvariable=self.expr_var, width=45)
        entry.pack(side=tk.LEFT, padx=5)
        entry.bind("<Return>", lambda e: self._plot())
        self.expr_entry = entry

        ttk.Label(top, text="X min:").pack(side=tk.LEFT, padx=(15, 2))
        self.xmin_var = tk.StringVar(value=str(self.x_min))
        ttk.Entry(top, textvariable=self.xmin_var, width=6).pack(side=tk.LEFT)

        ttk.Label(top, text="X max:").pack(side=tk.LEFT, padx=(8, 2))
        self.xmax_var = tk.StringVar(value=str(self.x_max))
        ttk.Entry(top, textvariable=self.xmax_var, width=6).pack(side=tk.LEFT)

        ttk.Button(top, text="Plot", command=self._plot).pack(side=tk.LEFT, padx=10)
        ttk.Button(top, text="Clear", command=self._clear_expr).pack(side=tk.LEFT)
        ttk.Button(top, text="Reset View", command=self._reset_view).pack(side=tk.LEFT, padx=5)

        hint = ttk.Label(
            self,
            text="Tip: separate multiple functions with commas. Scroll canvas to zoom, "
                 "click+drag to pan. Use the tabs below to build polynomials or insert "
                 "trig/inverse-trig functions instead of typing them by hand.",
            padding=(8, 0, 8, 4), wraplength=960, justify="left",
        )
        hint.pack(side=tk.TOP, fill=tk.X)

        nb = ttk.Notebook(self)
        nb.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 4))

        self._build_polynomial_tab(nb)
        self._build_trig_tab(nb, "Trig Functions", TRIG_FUNCS)
        self._build_trig_tab(nb, "Inverse Trig Functions", INV_TRIG_FUNCS)

        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.canvas.bind("<Configure>", lambda e: self._plot())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<MouseWheel>", self._on_scroll)   # Windows / macOS
        self.canvas.bind("<Button-4>", self._on_scroll)     # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_scroll)     # Linux scroll down

    def _build_polynomial_tab(self, nb):
        frame = ttk.Frame(nb, padding=8)
        nb.add(frame, text="Polynomial Builder (any power of x)")

        ttk.Label(frame, text="Degree:").grid(row=0, column=0, sticky="w")
        self.degree_var = tk.IntVar(value=2)
        ttk.Spinbox(frame, from_=0, to=10, width=4, textvariable=self.degree_var,
                    command=self._rebuild_coeff_fields).grid(row=0, column=1, sticky="w", padx=(4, 15))

        quick = ttk.Frame(frame)
        quick.grid(row=0, column=2, columnspan=6, sticky="w")
        for label, deg in [("Linear (1)", 1), ("Quadratic (2)", 2),
                            ("Cubic (3)", 3), ("Quartic (4)", 4)]:
            ttk.Button(quick, text=label,
                       command=lambda d=deg: self._set_degree(d)).pack(side=tk.LEFT, padx=2)

        self.coeff_frame = ttk.Frame(frame)
        self.coeff_frame.grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 4))
        self.coeff_vars = []
        self._rebuild_coeff_fields()

        ttk.Button(frame, text="Add to f(x)",
                   command=self._add_polynomial).grid(row=2, column=0, columnspan=2,
                                                        sticky="w", pady=(4, 0))

    def _set_degree(self, d):
        self.degree_var.set(d)
        self._rebuild_coeff_fields()

    def _rebuild_coeff_fields(self):
        for child in self.coeff_frame.winfo_children():
            child.destroy()
        self.coeff_vars = []
        degree = self.degree_var.get()
        for power in range(degree, -1, -1):
            default = "1" if power == degree else "0"
            var = tk.StringVar(value=default)
            self.coeff_vars.append((power, var))
            col = degree - power
            label = f"x^{power}" if power > 1 else ("x" if power == 1 else "1")
            ttk.Label(self.coeff_frame, text=f"({label}) coeff:").grid(
                row=0, column=2 * col, sticky="e", padx=(6, 2))
            ttk.Entry(self.coeff_frame, textvariable=var, width=5).grid(
                row=0, column=2 * col + 1, sticky="w")

    def _add_polynomial(self):
        terms = []
        try:
            for power, var in self.coeff_vars:
                c = float(var.get())
                if c == 0:
                    continue
                if power == 0:
                    terms.append(f"{c:g}")
                elif power == 1:
                    terms.append(f"{c:g}*x")
                else:
                    terms.append(f"{c:g}*x**{power}")
        except ValueError:
            messagebox.showerror("Invalid coefficient", "Coefficients must be numbers.")
            return
        expr = " + ".join(terms).replace("+ -", "- ") if terms else "0"
        self._append_expr(expr)

    def _build_trig_tab(self, nb, title, funcs):
        frame = ttk.Frame(nb, padding=8)
        nb.add(frame, text=title)
        ttk.Label(frame, text="Click a function to add it to f(x):").pack(anchor="w")
        btn_row = ttk.Frame(frame)
        btn_row.pack(anchor="w", pady=(6, 0))
        for f in funcs:
            ttk.Button(btn_row, text=f, width=9,
                       command=lambda f=f: self._append_expr(f)).pack(side=tk.LEFT, padx=3)

    def _append_expr(self, expr):
        current = self.expr_var.get().strip()
        if not current:
            self.expr_var.set(expr)
        else:
            self.expr_var.set(current + ", " + expr)
        self._plot()

    def _clear_expr(self):
        self.expr_var.set("")
        self._plot()

    def _reset_view(self):
        self.x_min, self.x_max = -10.0, 10.0
        self.y_min, self.y_max = -10.0, 10.0
        self.xmin_var.set(str(self.x_min))
        self.xmax_var.set(str(self.x_max))
        self._plot()

    # ------------------------------------------------------- coord helpers
    def _to_screen(self, x, y, w, h):
        sx = (x - self.x_min) / (self.x_max - self.x_min) * w
        sy = h - (y - self.y_min) / (self.y_max - self.y_min) * h
        return sx, sy

    def _to_math(self, sx, sy, w, h):
        x = self.x_min + sx / w * (self.x_max - self.x_min)
        y = self.y_min + (h - sy) / h * (self.y_max - self.y_min)
        return x, y

    # -------------------------------------------------------------- events
    def _on_press(self, event):
        self._drag_start = (event.x, event.y)

    def _on_drag(self, event):
        if self._drag_start is None:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        mx = dx / w * (self.x_max - self.x_min)
        my = dy / h * (self.y_max - self.y_min)
        self.x_min -= mx
        self.x_max -= mx
        self.y_min += my
        self.y_max += my
        self._drag_start = (event.x, event.y)
        self.xmin_var.set(f"{self.x_min:.3g}")
        self.xmax_var.set(f"{self.x_max:.3g}")
        self._plot()

    def _on_scroll(self, event):
        delta = event.delta if event.delta else (120 if event.num == 4 else -120)
        factor = 0.9 if delta > 0 else 1.1

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        mx, my = self._to_math(event.x, event.y, w, h)

        self.x_min = mx + (self.x_min - mx) * factor
        self.x_max = mx + (self.x_max - mx) * factor
        self.y_min = my + (self.y_min - my) * factor
        self.y_max = my + (self.y_max - my) * factor

        self.xmin_var.set(f"{self.x_min:.3g}")
        self.xmax_var.set(f"{self.x_max:.3g}")
        self._plot()

    # ---------------------------------------------------------------- core
    def _nice_step(self, span, target_ticks=10):
        if span <= 0:
            return 1.0
        raw = span / target_ticks
        magnitude = 10 ** math.floor(math.log10(raw))
        for m in (1, 2, 5, 10):
            step = m * magnitude
            if step >= raw:
                return step
        return 10 * magnitude

    def _plot(self):
        try:
            self.x_min = float(self.xmin_var.get())
            self.x_max = float(self.xmax_var.get())
        except ValueError:
            messagebox.showerror("Invalid range", "X min/max must be numbers.")
            return
        if self.x_min >= self.x_max:
            messagebox.showerror("Invalid range", "X min must be less than X max.")
            return

        if self.y_min >= self.y_max:
            self.y_min, self.y_max = -10.0, 10.0

        w = self.canvas.winfo_width() or 900
        h = self.canvas.winfo_height() or 500
        self.canvas.delete("all")

        self._draw_grid(w, h)
        self._draw_axes(w, h)

        exprs = [e.strip() for e in self.expr_var.get().split(",") if e.strip()]
        legend_y = 10
        for i, expr in enumerate(exprs):
            color = COLORS[i % len(COLORS)]
            ok = self._draw_function(expr, w, h, color)
            self.canvas.create_line(w - 90, legend_y + 8, w - 70, legend_y + 8,
                                     fill=color, width=3)
            label = expr if ok else f"{expr} (error)"
            self.canvas.create_text(w - 65, legend_y + 8, anchor="w",
                                     text=label, font=("TkDefaultFont", 9),
                                     fill="black" if ok else "gray")
            legend_y += 18

    def _draw_grid(self, w, h):
        x_step = self._nice_step(self.x_max - self.x_min)
        y_step = self._nice_step(self.y_max - self.y_min)

        x = math.ceil(self.x_min / x_step) * x_step
        while x <= self.x_max:
            sx, _ = self._to_screen(x, 0, w, h)
            self.canvas.create_line(sx, 0, sx, h, fill="#e8e8e8")
            if abs(x) > x_step / 1000:
                self.canvas.create_text(sx, h - 10, text=f"{x:g}",
                                         font=("TkDefaultFont", 8), fill="#666")
            x += x_step

        y = math.ceil(self.y_min / y_step) * y_step
        while y <= self.y_max:
            _, sy = self._to_screen(0, y, w, h)
            self.canvas.create_line(0, sy, w, sy, fill="#e8e8e8")
            if abs(y) > y_step / 1000:
                self.canvas.create_text(25, sy, text=f"{y:g}",
                                         font=("TkDefaultFont", 8), fill="#666")
            y += y_step

    def _draw_axes(self, w, h):
        if self.y_min <= 0 <= self.y_max:
            _, sy0 = self._to_screen(0, 0, w, h)
            self.canvas.create_line(0, sy0, w, sy0, fill="black", width=2)
        if self.x_min <= 0 <= self.x_max:
            sx0, _ = self._to_screen(0, 0, w, h)
            self.canvas.create_line(sx0, 0, sx0, h, fill="black", width=2)

    def _draw_function(self, expr, w, h, color):
        samples = max(300, w)
        points = []
        prev_y = None
        drew_anything = False

        for i in range(samples + 1):
            x = self.x_min + (self.x_max - self.x_min) * i / samples
            try:
                y = eval(expr, {"__builtins__": {}}, {**SAFE_NAMES, "x": x})
                if isinstance(y, complex):
                    raise ValueError("complex result")
                y = float(y)
                if math.isnan(y) or math.isinf(y):
                    raise ValueError("nan/inf")
            except Exception:
                if len(points) > 1:
                    self.canvas.create_line(points, fill=color, width=2, smooth=False)
                    drew_anything = True
                points = []
                prev_y = None
                continue

            sx, sy = self._to_screen(x, y, w, h)

            if prev_y is not None and abs(sy - prev_y) > h * 1.5:
                if len(points) > 1:
                    self.canvas.create_line(points, fill=color, width=2, smooth=False)
                    drew_anything = True
                points = []

            points.append((sx, sy))
            prev_y = sy

        if len(points) > 1:
            self.canvas.create_line(points, fill=color, width=2, smooth=False)
            drew_anything = True

        return drew_anything


if __name__ == "__main__":
    app = GraphPlotter()
    app.mainloop()
