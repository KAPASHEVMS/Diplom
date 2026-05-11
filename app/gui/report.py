"""Отчёт по утверждённым ценам и динамике конкурентов."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from decimal import Decimal

from sqlalchemy import select, func

from ..db import SessionLocal
from ..models import Product, ProductShop, CompetitorPrice, Shop, Brand


class ReportFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        bar = ttk.Frame(self); bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(bar, text="Экспорт в CSV", command=self.export_csv).pack(side="left", padx=4)
        self.summary = tk.StringVar(value="Готово.")
        ttk.Label(bar, textvariable=self.summary, font=("Arial", 10, "italic")).pack(side="right")

        cols = ("sku","name","brand","cost","pmin","pmax","approved","margin","competitors")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=24)
        for c, t, w in [
            ("sku","Артикул",120), ("name","Наименование",280),
            ("brand","Бренд",100),
            ("cost","Себест., ₽",100), ("pmin","Pmin, ₽",90),
            ("pmax","Pmax, ₽",90), ("approved","Утв. P*, ₽",100),
            ("margin","Маржа, %",90), ("competitors","Конкур.",80),
        ]:
            self.tree.heading(c, text=t); self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)
        self.refresh()

    def _query(self):
        rows = []
        with SessionLocal() as s:
            products = s.execute(select(Product)).scalars().all()
            total_margin = Decimal("0"); n_appr = 0
            for p in products:
                brand = s.get(Brand, p.id_brand).name if p.id_brand else "—"
                ps = s.execute(
                    select(ProductShop).where(ProductShop.id_product == p.id_product)
                ).scalar_one_or_none()
                n_competitors = s.execute(
                    select(func.count(CompetitorPrice.id))
                    .where(CompetitorPrice.id_product == p.id_product)
                ).scalar()
                approved = ps.approved_price if ps and ps.approved_price else None
                pmin = ps.price_min if ps else None
                pmax = ps.price_max if ps else None
                margin = None
                if approved and p.cost and p.cost > 0:
                    margin = (approved - p.cost) / p.cost * Decimal("100")
                    total_margin += margin
                    n_appr += 1
                rows.append({
                    "sku": p.sku, "name": p.name, "brand": brand,
                    "cost": p.cost, "pmin": pmin, "pmax": pmax,
                    "approved": approved, "margin": margin,
                    "competitors": n_competitors,
                })
            avg = total_margin / Decimal(n_appr) if n_appr else None
            self._avg_margin = avg
            self._approved_n = n_appr
        return rows

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        rows = self._query()
        for r in rows:
            self.tree.insert("", "end", values=(
                r["sku"], r["name"], r["brand"],
                f"{r['cost']:.0f}"      if r["cost"]      else "—",
                f"{r['pmin']:.0f}"      if r["pmin"]      else "—",
                f"{r['pmax']:.0f}"      if r["pmax"]      else "—",
                f"{r['approved']:.0f}"  if r["approved"]  else "—",
                f"{r['margin']:.1f}"    if r["margin"]    else "—",
                r["competitors"],
            ))
        if self._approved_n:
            self.summary.set(f"Утверждено товаров: {self._approved_n}, "
                             f"средняя маржа: {self._avg_margin:.1f} %")
        else:
            self.summary.set(f"Утверждённых цен ещё нет.")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV","*.csv")])
        if not path: return
        import csv
        rows = self._query()
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["sku","name","brand","cost","pmin","pmax",
                        "approved","margin_percent","competitors"])
            for r in rows:
                w.writerow([
                    r["sku"], r["name"], r["brand"],
                    r["cost"], r["pmin"], r["pmax"],
                    r["approved"],
                    f"{r['margin']:.2f}" if r["margin"] else "",
                    r["competitors"],
                ])
        messagebox.showinfo("Готово", f"Сохранено: {path}")
