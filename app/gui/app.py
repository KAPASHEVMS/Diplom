"""Главное окно Tkinter-приложения.

Структура: корневой Tk показывается сразу. Сначала рисуем форму логина как
обычный фрейм внутри root, после успешного входа удаляем этот фрейм и строим
основной интерфейс с вкладками.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from ..db import SessionLocal, check_connection
from ..config import settings
from ..models import AppUser
from ..auth import authenticate
from .catalog import CatalogFrame
from .price_form import PriceFormFrame
from .report import ReportFrame
from .settings_frame import SettingsFrame


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ПИС расчёта конечной рыночной цены товаров")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        self.user: AppUser | None = None

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", font=("Arial", 10))
        style.configure("TLabel", font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        self._show_login()

    # ---------- Login screen ----------
    def _show_login(self):
        self.login_frame = ttk.Frame(self)
        self.login_frame.pack(fill="both", expand=True)

        # Центральный блок
        center = ttk.Frame(self.login_frame)
        center.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(center, text="ПИС расчёта конечной рыночной цены",
                  font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2,
                                                    pady=(0, 16))
        ttk.Label(center, text="Вход в систему",
                  font=("Arial", 12)).grid(row=1, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(center, text="Логин").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.login_var = tk.StringVar(value=settings.default_user)
        login_ent = ttk.Entry(center, textvariable=self.login_var, width=28)
        login_ent.grid(row=2, column=1, pady=4, padx=8)

        ttk.Label(center, text="Пароль").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.pwd_var = tk.StringVar(value=settings.default_password)
        ttk.Entry(center, textvariable=self.pwd_var, show="*", width=28).grid(
            row=3, column=1, pady=4, padx=8)

        self.login_status = tk.StringVar(value="Проверка подключения к БД…")
        ttk.Label(center, textvariable=self.login_status,
                  font=("Arial", 9, "italic"), foreground="#555").grid(
                      row=4, column=0, columnspan=2, pady=(12, 4))

        ttk.Button(center, text="Войти", command=self._do_login).grid(
            row=5, column=0, columnspan=2, sticky="we", padx=8, pady=12)
        ttk.Button(center, text="Повторить проверку БД",
                   command=self._check_db).grid(
            row=6, column=0, columnspan=2, sticky="we", padx=8, pady=(0, 4))

        self.bind("<Return>", lambda e: self._do_login())
        login_ent.focus_set()

        # Проверяем БД асинхронно после показа окна
        self.after(100, self._check_db)

    def _check_db(self):
        ok, msg = check_connection()
        if ok:
            self.login_status.set("Подключение к БД установлено.")
        else:
            # Сокращаем сообщение
            short = msg.replace("\n", " ")
            if len(short) > 160:
                short = short[:160] + "…"
            self.login_status.set(f"Нет подключения к БД: {short}")

    def _do_login(self):
        login = self.login_var.get().strip()
        password = self.pwd_var.get()
        if not login or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        try:
            with SessionLocal() as s:
                user = authenticate(s, login, password)
        except Exception as e:
            messagebox.showerror(
                "Ошибка подключения к БД",
                f"Не удалось подключиться к БД.\n\n{e}\n\n"
                "Проверьте, что запущен docker compose (контейнер pricing_db) "
                "и переменная DATABASE_URL указывает на нужный хост.")
            return

        if user is None:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return

        self.user = user
        self.login_frame.destroy()
        self._build_layout()

    # ---------- Main interface ----------
    def _build_layout(self):
        top = ttk.Frame(self); top.pack(fill="x", side="top")
        ttk.Label(top, text=f"Пользователь: {self.user.login}  ({self.user.role})",
                  font=("Arial", 10, "italic")).pack(side="left", padx=8, pady=4)
        ttk.Label(top, text="ПИС расчёта конечной рыночной цены товаров",
                  font=("Arial", 12, "bold")).pack(side="left", expand=True)
        ttk.Button(top, text="Выход", command=self.destroy).pack(side="right",
                                                                  padx=8, pady=4)

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=8, pady=4)
        self.catalog = CatalogFrame(nb, app=self)
        self.price = PriceFormFrame(nb, app=self)
        self.report = ReportFrame(nb, app=self)
        self.settings_tab = SettingsFrame(nb, app=self)

        nb.add(self.catalog, text="Каталог товаров")
        nb.add(self.price, text="Расчёт цены")
        nb.add(self.report, text="Отчёты")
        nb.add(self.settings_tab, text="Настройки моделей")

        self.catalog.bind_selection(self._on_product_selected)

    def _on_product_selected(self, product_id: int):
        self.price.load_product(product_id)


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
