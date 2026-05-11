"""Главное окно Tkinter-приложения."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from ..db import SessionLocal
from ..models import AppUser
from ..auth import authenticate
from .catalog import CatalogFrame
from .price_form import PriceFormFrame
from .report import ReportFrame
from .settings_frame import SettingsFrame


class LoginDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Вход в систему")
        self.geometry("420x240")
        self.resizable(False, False)
        self.user: AppUser | None = None

        ttk.Label(self, text="ПИС расчёта цены", font=("Arial", 14, "bold")).pack(pady=12)
        frm = ttk.Frame(self); frm.pack(padx=24, pady=4, fill="x")

        ttk.Label(frm, text="Логин").grid(row=0, column=0, sticky="w", pady=4)
        self.login_var = tk.StringVar(value="manager")
        ttk.Entry(frm, textvariable=self.login_var, width=30).grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="Пароль").grid(row=1, column=0, sticky="w", pady=4)
        self.pwd_var = tk.StringVar(value="manager123")
        ttk.Entry(frm, textvariable=self.pwd_var, show="*", width=30).grid(row=1, column=1, pady=4)

        btn = ttk.Button(self, text="Войти", command=self._on_login)
        btn.pack(pady=12)
        self.bind("<Return>", lambda e: self._on_login())

        self.grab_set()
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", master.destroy)

    def _on_login(self):
        with SessionLocal() as s:
            user = authenticate(s, self.login_var.get().strip(), self.pwd_var.get())
        if user is None:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return
        self.user = user
        self.destroy()


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ПИС расчёта конечной рыночной цены товаров")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        self.user: AppUser | None = None

        # Стиль
        style = ttk.Style(self)
        # tkinter on Windows looks fine with 'vista' or 'clam'
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", font=("Arial", 10))
        style.configure("TLabel", font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        # Сначала логин
        self.withdraw()
        dlg = LoginDialog(self)
        self.wait_window(dlg)
        if dlg.user is None:
            self.destroy(); return
        self.user = dlg.user
        self.deiconify()
        self._build_layout()

    def _build_layout(self):
        # Top bar
        top = ttk.Frame(self); top.pack(fill="x", side="top")
        ttk.Label(top, text=f"Пользователь: {self.user.login}  ({self.user.role})",
                  font=("Arial", 10, "italic")).pack(side="left", padx=8, pady=4)
        ttk.Label(top, text="ПИС расчёта конечной рыночной цены товаров",
                  font=("Arial", 12, "bold")).pack(side="left", expand=True)
        ttk.Button(top, text="Выход", command=self.destroy).pack(side="right", padx=8, pady=4)

        # Notebook
        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=8, pady=4)
        self.catalog = CatalogFrame(nb, app=self)
        self.price   = PriceFormFrame(nb, app=self)
        self.report  = ReportFrame(nb, app=self)
        self.settings_tab = SettingsFrame(nb, app=self)

        nb.add(self.catalog, text="Каталог товаров")
        nb.add(self.price,   text="Расчёт цены")
        nb.add(self.report,  text="Отчёты")
        nb.add(self.settings_tab, text="Настройки моделей")

        # When catalog selection changes, push it to price form
        self.catalog.bind_selection(self._on_product_selected)

    def _on_product_selected(self, product_id: int):
        self.price.load_product(product_id)


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
