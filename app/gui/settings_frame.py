"""Вкладка настроек: ценовые модели и ручной запуск парсера."""
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from sqlalchemy import select

from ..db import SessionLocal
from ..models import MType
from ..parsers.runner import run_once


class SettingsFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        # Top — pricing models list
        top = ttk.LabelFrame(self, text="Ценовые модели")
        top.pack(fill="x", padx=8, pady=8)

        cols = ("code","name","params")
        self.tree = ttk.Treeview(top, columns=cols, show="headings", height=6)
        for c, t, w in [("code","Код",120),("name","Название",240),("params","Параметры",520)]:
            self.tree.heading(c, text=t); self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="x", padx=4, pady=4)
        self._reload_models()

        # Parser controls
        prsr = ttk.LabelFrame(self, text="Парсер цен конкурентов")
        prsr.pack(fill="x", padx=8, pady=8)
        ttk.Label(prsr, text="Запуск парсинга вручную (по всем товарам, по текущему режиму "
                              "PARSER_MODE из окружения).",
                  wraplength=900, justify="left").pack(anchor="w", padx=8, pady=6)
        self.parser_status = tk.StringVar(value="Готово.")
        ttk.Label(prsr, textvariable=self.parser_status, font=("Arial", 10, "italic")).pack(
            anchor="w", padx=8)
        ttk.Button(prsr, text="Запустить парсинг сейчас",
                   command=self._run_parser).pack(anchor="w", padx=8, pady=8)

        # Info block
        info = ttk.LabelFrame(self, text="Сведения")
        info.pack(fill="both", expand=True, padx=8, pady=8)
        msg = tk.Text(info, height=10, wrap="word")
        msg.insert("1.0",
            "Формулы используемых моделей:\n\n"
            "Себестоимость: C = P0 + P0·α + (P0+P0·α)·β + (P0+P0·α+(P0+P0·α)·β)·γ\n"
            "  α — транспорт, β — таможня, γ — косвенные.\n\n"
            "Затратная модель: Pmin = C·(1 + m_low), Pmax = C·(1 + m_high)\n"
            "Рыночная модель:   Pmin = min(P_market), Pmax = max(P_market)\n"
            "Комбинированная:   Pmin = max(C·k, Q25(P_market)),\n"
            "                   Pmax = min(C·K, Q75(P_market))\n\n"
            "Утверждение: P* ∈ [Pmin; Pmax]. При нарушении — возврат на перерасчёт.")
        msg.config(state="disabled")
        msg.pack(fill="both", expand=True, padx=4, pady=4)

    def _reload_models(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        with SessionLocal() as s:
            for m in s.execute(select(MType)).scalars().all():
                self.tree.insert("", "end", values=(m.code, m.name, m.params))

    def _run_parser(self):
        if self.app.user.role not in ("admin", "manager"):
            messagebox.showerror("Доступ", "Только администратор и менеджер")
            return
        self.parser_status.set("Парсинг… подождите")
        def worker():
            try:
                run_once()
                self.parser_status.set("Парсинг завершён, цены обновлены.")
            except Exception as e:  # pragma: no cover
                self.parser_status.set(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()
