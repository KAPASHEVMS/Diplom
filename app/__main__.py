"""Запуск GUI: `python -m app`"""
import sys

if __name__ == "__main__":
    print("[ПИС] запуск GUI…", flush=True)
    try:
        from app.gui.app import main
        main()
    except KeyboardInterrupt:
        print("[ПИС] прервано пользователем", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[ПИС] ОШИБКА: {type(e).__name__}: {e}", flush=True)
        import traceback; traceback.print_exc()
        sys.exit(1)
