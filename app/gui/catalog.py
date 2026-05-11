"""Каталог товаров с поиском, добавлением и кнопкой импорта прайс-листа."""
from __future__ import annotations
import csv
import tkinter as tk
from decimal import Decimal
from tkinter import ttk, messagebox, filedialog, simpledialog

from sqlalchemy import select

from ..db import SessionLocal
from ..models import Product, Brand, VType, ProductShop


class CatalogFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._selection_callbacks: list = []

        # Top toolbar
        bar = ttk.Frame(self); bar.pack(fill="x", padx=4, pady=4)
        ttk.Label(bar, text="Поиск:").pack(side="left")
        self.q = tk.StringVar()
        ent = ttk.Entry(bar, textvariable=self.q, width=40)
        ent.pack(side="left", padx=4)
        ent.bind("<KeyRelease>", lambda e: self.refresh())
        ttk.Button(bar, text="+ Товар", command=self._add_product).pack(side="left", padx=2)
        ttk.Button(bar, text="Импорт CSV", command=self._import_csv).pack(side="left", padx=2)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=2)

        # Tree
        cols = ("sku","name","brand","vtype","purchase","cost","band","approved")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=22)
        for c, t, w in [
            ("sku","Артикул",140), ("name","Наименование",320),
            ("brand","Бренд",120), ("vtype","Вид",90),
            ("purchase","Закуп., ₽",110), ("cost","Себест., ₽",110),
            ("band","Вилка, ₽",170), ("approved","Утв. цена, ₽",120),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def bind_selection(self, cb):
        self._selection_callbacks.append(cb)

    def _on_select(self, _e=None):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        for cb in self._selection_callbacks:
            cb(pid)

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        q = self.q.get().strip().lower()
        with SessionLocal() as s:
            rows = s.execute(select(Product)).scalars().all()
            for p in rows:
                if q and q not in (p.name or "").lower() and q not in (p.sku or "").lower():
                    continue
                brand = s.get(Brand, p.id_brand).name if p.id_brand else "—"
                vtype = s.get(VType, p.id_v_type).name if p.id_v_type else "—"
                ps = s.execute(
                    select(ProductShop).where(ProductShop.id_product == p.id_product)
                ).scalar_one_or_none()
                band = f"{ps.price_min:.0f} – {ps.price_max:.0f}" if ps and ps.price_min and ps.price_max else "—"
                appr = f"{ps.approved_price:.0f}" if ps and ps.approved_price else "—"
                cost = f"{p.cost:.0f}" if p.cost else "—"
                self.tree.insert("", "end", iid=str(p.id_product), values=(
                    p.sku, p.name, brand, vtype,
                    f"{p.purchase_price:.0f}", cost, band, appr,
                ))

    def _add_product(self):
        with SessionLocal() as s:
            brands = s.execute(select(Brand)).scalars().all()
            vtypes = s.execute(select(VType)).scalars().all()
        dlg = AddProductDialog(self, brands, vtypes)
        self.wait_window(dlg)
        if dlg.result:
            d = dlg.result
            with SessionLocal() as s:
                p = Product(
                    sku=d["sku"], name=d["name"],
                    id_brand=d["id_brand"], id_v_type=d["id_v_type"],
                    purchase_price=Decimal(d["purchase_price"]),
                    search_query=d["search_query"],
                )
                s.add(p); s.commit()
            self.refresh()

    def _import_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV-файл","*.csv"),("Все файлы","*.*")])
        if not path: return
        added = 0; skipped = 0
        with open(path, encoding="utf-8") as f, SessionLocal() as s:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                sku = (row.get("sku") or "").strip()
                if not sku: continue
                exists = s.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
                if exists:
                    # обновим закупочную
                    if row.get("purchase_price"):
                        exists.purchase_price = Decimal(row["purchase_price"])
                    skipped += 1
                else:
                    s.add(Product(
                        sku=sku, name=row.get("name","").strip(),
                        purchase_price=Decimal(row.get("purchase_price","0")),
                        search_query=(row.get("search_query") or row.get("name") or "").strip(),
                    ))
                    added += 1
            s.commit()
        messagebox.showinfo("Импорт CSV", f"Добавлено: {added}\nОбновлено: {skipped}")
        self.refresh()


class AddProductDialog(tk.Toplevel):
    def __init__(self, master, brands, vtypes):
        super().__init__(master)
        self.title("Добавить товар")
        self.result = None
        self.geometry("440x320"); self.resizable(False, False)
        frm = ttk.Frame(self); frm.pack(padx=12, pady=12, fill="both", expand=True)

        self.sku = tk.StringVar()
        self.name = tk.StringVar()
        self.pp   = tk.StringVar(value="0")
        self.sq   = tk.StringVar()
        self.brand_id = tk.StringVar()
        self.vtype_id = tk.StringVar()

        rows = [
            ("Артикул (SKU)", self.sku, None),
            ("Наименование", self.name, None),
            ("Закупочная цена, ₽", self.pp, None),
            ("Поисковый запрос", self.sq, None),
        ]
        for i, (lbl, var, _) in enumerate(rows):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(frm, textvariable=var, width=32).grid(row=i, column=1, pady=4)

        ttk.Label(frm, text="Бренд").grid(row=4, column=0, sticky="w", pady=4)
        brand_combo = ttk.Combobox(frm, values=[b.name for b in brands],
                                    textvariable=self.brand_id, width=30)
        brand_combo.grid(row=4, column=1, pady=4)
        self._brands_map = {b.name: b.id_brand for b in brands}

        ttk.Label(frm, text="Вид товара").grid(row=5, column=0, sticky="w", pady=4)
        vtype_combo = ttk.Combobox(frm, values=[v.name for v in vtypes],
                                    textvariable=self.vtype_id, width=30)
        vtype_combo.grid(row=5, column=1, pady=4)
        self._vtypes_map = {v.name: v.id_v_type for v in vtypes}

        ttk.Button(frm, text="Сохранить", command=self._on_ok).grid(row=6, column=1, sticky="e", pady=12)
        self.bind("<Return>", lambda e: self._on_ok())

    def _on_ok(self):
        if not self.sku.get() or not self.name.get():
            messagebox.showerror("Ошибка","Заполните артикул и наименование"); return
        self.result = {
            "sku": self.sku.get().strip(),
            "name": self.name.get().strip(),
            "purchase_price": self.pp.get().strip() or "0",
            "search_query": self.sq.get().strip() or self.name.get().strip(),
            "id_brand": self._brands_map.get(self.brand_id.get()),
            "id_v_type": self._vtypes_map.get(self.vtype_id.get()),
        }
        self.destroy()
