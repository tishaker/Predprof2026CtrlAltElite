import os
import sys
import time
import subprocess
from pathlib import Path

def check_dependencies():
    try:
        import flask
        import pandas
        import sqlalchemy
        return True
    except ImportError as e:
        return False

def generate_csv_if_needed():
    csv_files = list(Path(".").glob("data_*.csv"))

    if len(csv_files) >= 16:
        return True
    try:
        result = subprocess.run(
            [sys.executable, "csvgen.py"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True
        else:
            return False

    except Exception as e:
        return False


def start_flask_server():
    flask_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    time.sleep(3)

    try:
        import requests
        response = requests.get("http://localhost:5000", timeout=3)
        if response.status_code in [200, 302]:
            print("Сервер запущен: http://localhost:5000")
            print("Логин: admin | Пароль: admin123")
            return flask_proc
    except:
        pass

    time.sleep(1)
    stdout, stderr = flask_proc.communicate(timeout=1)

    if "Running on" in stdout or "Running on" in stderr:
        print("⚠️  Сервер запущен (проверьте вручную)")
        print("   Ссылка: http://localhost:5000")

        return flask_proc

    if stderr:
        print(f"Ошибка: {stderr[:200]}")

    flask_proc.terminate()
    return None


def main():
    if not check_dependencies():
        return

    if not generate_csv_if_needed():
        return

    flask_process = start_flask_server()
    if not flask_process:
        return
    try:
        flask_process.wait()
    except KeyboardInterrupt:
        flask_process.terminate()
    except:
        flask_process.terminate()
if __name__ == "__main__":
    main()