"""Форма расчёта цены товара."""
from __future__ import annotations
import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import ttk, messagebox

from sqlalchemy import select, desc

from ..db import SessionLocal
from ..models import Product, ProductShop, MType, CompetitorPrice, AuditLog
from ..pricing import (
    CostCoefficients, calculate_full_cost,
    PricingModel, BandParams, build_band, approve_price,
)
from ..pricing.approval import PriceOutOfBandError


class PriceFormFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.product_id: int | None = None
        self._build()

    def _build(self):
        wrap = ttk.Frame(self); wrap.pack(fill="both", expand=True, padx=8, pady=8)

        # === Left column: parameters
        left = ttk.LabelFrame(wrap, text="Параметры расчёта")
        left.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.lbl_product = ttk.Label(left, text="(товар не выбран)",
                                     font=("Arial", 11, "bold"))
        self.lbl_product.grid(row=0, column=0, columnspan=2, pady=8, sticky="w", padx=8)

        self.purchase = tk.StringVar(value="0")
        self.alpha    = tk.StringVar(value="0.05")
        self.beta     = tk.StringVar(value="0.12")
        self.gamma    = tk.StringVar(value="0.08")
        self.m_low    = tk.StringVar(value="0.20")
        self.m_high   = tk.StringVar(value="0.55")
        self.k_low    = tk.StringVar(value="1.20")
        self.k_high   = tk.StringVar(value="1.55")
        self.model    = tk.StringVar(value="combined")

        rows = [
            ("Закупочная цена P0, ₽",     self.purchase),
            ("Транспорт α",                self.alpha),
            ("Таможня β",                  self.beta),
            ("Косвенные γ",                self.gamma),
            ("Маржа нижняя m_low",         self.m_low),
            ("Маржа верхняя m_high",       self.m_high),
            ("Множитель k (комбин., нижн)",self.k_low),
            ("Множитель K (комбин., верх)",self.k_high),
        ]
        for i, (lbl, var) in enumerate(rows, start=1):
            ttk.Label(left, text=lbl).grid(row=i, column=0, sticky="w", padx=8, pady=2)
            ttk.Entry(left, textvariable=var, width=14).grid(row=i, column=1, sticky="w", pady=2)

        ttk.Label(left, text="Модель").grid(row=len(rows)+1, column=0, sticky="w", padx=8, pady=4)
        ttk.Combobox(left, textvariable=self.model, width=14,
                     values=["cost","market","combined"]).grid(row=len(rows)+1, column=1, sticky="w")

        ttk.Button(left, text="Пересчитать", command=self.recalc).grid(
            row=len(rows)+2, column=0, columnspan=2, sticky="we", padx=8, pady=10)

        # === Right column: results
        right = ttk.LabelFrame(wrap, text="Результат")
        right.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        self.cost_lbl     = self._kv(right, "Себестоимость C, ₽", 0)
        self.pmin_lbl     = self._kv(right, "Pmin, ₽", 1)
        self.pmax_lbl     = self._kv(right, "Pmax, ₽", 2)
        self.market_avg   = self._kv(right, "Среднерыночная, ₽", 3)
        self.market_n     = self._kv(right, "Цен конкурентов", 4)
        self.recommend    = self._kv(right, "Рекомендованная P*, ₽", 5)

        ttk.Separator(right, orient="horizontal").grid(row=6, column=0, columnspan=2,
                                                       sticky="we", pady=6, padx=8)
        ttk.Label(right, text="Утвердить цену P*:").grid(row=7, column=0, sticky="w", padx=8, pady=4)
        self.p_star = tk.StringVar()
        ttk.Entry(right, textvariable=self.p_star, width=14).grid(row=7, column=1, sticky="w")
        ttk.Button(right, text="Утвердить",
                   command=self.approve).grid(row=8, column=0, columnspan=2, sticky="we",
                                              padx=8, pady=6)
        ttk.Button(right, text="На перерасчёт",
                   command=self.reject).grid(row=9, column=0, columnspan=2, sticky="we",
                                              padx=8, pady=2)

        # Competitor prices table
        prices_frame = ttk.LabelFrame(self, text="Цены конкурентов")
        prices_frame.pack(fill="x", expand=False, padx=8, pady=8)
        cols = ("shop","price","fetched","url")
        self.cp_tree = ttk.Treeview(prices_frame, columns=cols, show="headings", height=6)
        for c, t, w in [("shop","Магазин",160),("price","Цена, ₽",100),
                         ("fetched","Когда",140),("url","Ссылка",520)]:
            self.cp_tree.heading(c, text=t); self.cp_tree.column(c, width=w, anchor="w")
        self.cp_tree.pack(fill="x", padx=4, pady=4)

    def _kv(self, parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=3)
        var = tk.StringVar(value="—")
        ttk.Label(parent, textvariable=var, font=("Arial", 11, "bold")).grid(
            row=row, column=1, sticky="w", padx=8, pady=3)
        return var

    # ---- Public API ----
    def load_product(self, product_id: int):
        self.product_id = product_id
        with SessionLocal() as s:
            p = s.get(Product, product_id)
            if p is None: return
            self.lbl_product.config(text=f"{p.sku}  •  {p.name}")
            if p.purchase_price:
                self.purchase.set(f"{p.purchase_price}")
            # Load competitor prices
            for i in self.cp_tree.get_children():
                self.cp_tree.delete(i)
            cps = s.execute(
                select(CompetitorPrice).where(CompetitorPrice.id_product == product_id)
                .order_by(desc(CompetitorPrice.fetched_at)).limit(50)
            ).scalars().all()
            for cp in cps:
                shop = cp.id_shop  # show id; could resolve to name
                from ..models import Shop
                sh = s.get(Shop, cp.id_shop)
                self.cp_tree.insert("", "end", values=(
                    sh.name if sh else cp.id_shop,
                    f"{cp.price:.0f}",
                    cp.fetched_at.strftime("%Y-%m-%d %H:%M"),
                    cp.url or "—",
                ))

    # ---- Calc ----
    def _read_decimal(self, var: tk.StringVar, name: str) -> Decimal:
        try:
            return Decimal(var.get().replace(",", "."))
        except (InvalidOperation, AttributeError):
            raise ValueError(f"Некорректное значение «{name}»: {var.get()!r}")

    def recalc(self):
        if self.product_id is None:
            messagebox.showwarning("", "Выберите товар на вкладке «Каталог»"); return
        try:
            p0 = self._read_decimal(self.purchase, "Закупочная цена")
            coeffs = CostCoefficients(
                transport=self._read_decimal(self.alpha, "α"),
                customs  =self._read_decimal(self.beta,  "β"),
                overhead =self._read_decimal(self.gamma, "γ"),
            )
            params = BandParams(
                margin_low =self._read_decimal(self.m_low,  "m_low"),
                margin_high=self._read_decimal(self.m_high, "m_high"),
                k_low      =self._read_decimal(self.k_low,  "k"),
                k_high     =self._read_decimal(self.k_high, "K"),
            )
            model = PricingModel(self.model.get())

            cost = calculate_full_cost(p0, coeffs)
            # collect competitor prices
            with SessionLocal() as s:
                cps = s.execute(
                    select(CompetitorPrice).where(CompetitorPrice.id_product == self.product_id)
                ).scalars().all()
                market = [Decimal(cp.price) for cp in cps]
                pmin, pmax = build_band(cost, market, model, params)
                # save into product_shop
                ps = s.execute(
                    select(ProductShop).where(ProductShop.id_product == self.product_id)
                ).scalar_one_or_none()
                if ps is None:
                    ps = ProductShop(id_product=self.product_id)
                    s.add(ps)
                ps.price_min = pmin
                ps.price_max = pmax
                # find m_type
                mt = s.execute(select(MType).where(MType.code == model.value)).scalar_one_or_none()
                if mt: ps.id_m_type = mt.id_m_type
                # also remember cost in product
                p = s.get(Product, self.product_id)
                p.cost = cost
                s.add(AuditLog(id_user=self.app.user.id_user, action="recalc",
                               target_id=self.product_id, payload=f"C={cost};band=[{pmin};{pmax}]"))
                s.commit()

            self.cost_lbl.set(f"{cost:.2f}")
            self.pmin_lbl.set(f"{pmin:.2f}")
            self.pmax_lbl.set(f"{pmax:.2f}")
            self.market_n.set(str(len(market)))
            if market:
                avg = sum(market) / Decimal(len(market))
                self.market_avg.set(f"{avg:.2f}")
                self.recommend.set(f"{((pmin + pmax) / Decimal('2')):.2f}")
                self.p_star.set(f"{((pmin + pmax) / Decimal('2')):.2f}")
            else:
                self.market_avg.set("нет данных")
                self.recommend.set(f"{((pmin + pmax) / Decimal('2')):.2f}")
            # refresh catalog table
            self.app.catalog.refresh()
        except Exception as e:
            messagebox.showerror("Ошибка расчёта", str(e))

    def approve(self):
        if self.product_id is None: return
        try:
            with SessionLocal() as s:
                ps = s.execute(
                    select(ProductShop).where(ProductShop.id_product == self.product_id)
                ).scalar_one_or_none()
                if ps is None:
                    messagebox.showwarning("", "Сначала пересчитайте вилку"); return
                p_star = self._read_decimal(self.p_star, "P*")
                approve_price(s, product_shop_id=ps.id_ps,
                              p_star=p_star, user_id=self.app.user.id_user)
            messagebox.showinfo("Готово", f"Цена {p_star} утверждена")
            self.app.catalog.refresh()
        except PriceOutOfBandError as e:
            messagebox.showerror("Вне вилки", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def reject(self):
        if self.product_id is None: return
        with SessionLocal() as s:
            s.add(AuditLog(id_user=self.app.user.id_user, action="reject",
                           target_id=self.product_id, payload="returned_for_recalc"))
            s.commit()
        messagebox.showinfo("Отправлено", "Запись возвращена на перерасчёт")
