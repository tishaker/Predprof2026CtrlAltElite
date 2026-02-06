#!/usr/bin/env python3
"""
АВТОМАТИЧЕСКИЙ ЗАПУСК ПРИЛОЖЕНИЯ
Запускает всё одной командой: python run.py
"""
import os
import sys
import time
import subprocess
from pathlib import Path


def print_step(step, message):
    """Красивый вывод шагов"""
    print(f"\n{'=' * 50}")
    print(f"🚀 {step}: {message}")
    print(f"{'=' * 50}")


def check_dependencies():
    """Проверяет установлены ли зависимости"""
    print_step(1, "ПРОВЕРКА ЗАВИСИМОСТЕЙ")

    try:
        import flask
        import pandas
        import sqlalchemy
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Не установлено: {e}")
        print("Установите: pip install -r requirements.txt")
        return False


def generate_csv_if_needed():
    """Генерирует CSV файлы если их нет"""
    print_step(2, "ПРОВЕРКА CSV ФАЙЛОВ")

    csv_files = list(Path(".").glob("data_*.csv"))

    if len(csv_files) >= 16:
        print(f"✅ Найдено {len(csv_files)} CSV файлов")
        return True

    print("📝 Генерирую CSV файлы...")
    try:
        result = subprocess.run(
            [sys.executable, "csvgen.py"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ CSV файлы созданы")
            return True
        else:
            print(f"❌ Ошибка: {result.stderr[:200]}")
            return False

    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return False


def start_flask_server():
    """Запускает Flask сервер"""
    print_step(3, "ЗАПУСК СЕРВЕРА")

    print("Запускаю Flask приложение...")

    # Запускаем app.py в отдельном процессе
    flask_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Ждем запуска сервера
    time.sleep(3)

    # Проверяем что сервер запустился
    try:
        import requests
        response = requests.get("http://localhost:5000", timeout=3)
        if response.status_code in [200, 302]:
            print("✅ Сервер запущен на http://localhost:5000")
            return flask_proc
    except:
        pass

    # Если не запустился - проверяем ошибки
    time.sleep(1)
    stdout, stderr = flask_proc.communicate(timeout=1)

    if "Running on" in stdout or "Running on" in stderr:
        print("✅ Сервер запущен (проверь вручную)")
        return flask_proc

    print("❌ Сервер не запустился")
    if stderr:
        print(f"Ошибка: {stderr[:200]}")

    flask_proc.terminate()
    return None


def main():
    """Главная функция запуска"""
    print("\n" + "=" * 60)
    print("🎓 ПРИЛОЖЕНИЕ 'ПРИЕМНАЯ КОМИССИЯ' - АВТОЗАПУСК")
    print("=" * 60)

    # 1. Проверяем зависимости
    if not check_dependencies():
        print("\n❌ Установите зависимости и перезапустите")
        return

    # 2. Генерируем CSV если нужно
    if not generate_csv_if_needed():
        print("\n❌ Не удалось создать данные")
        return

    # 3. Запускаем сервер
    flask_process = start_flask_server()
    if not flask_process:
        print("\n❌ Не удалось запустить сервер")
        return

    # 4. Инструкция для пользователя
    print_step(4, "ПРИЛОЖЕНИЕ ГОТОВО!")

    print("\n📱 ОТКРОЙТЕ В БРАУЗЕРЕ:")
    print("   http://localhost:5000")
    print("\n🔐 ДАННЫЕ ДЛЯ ВХОДА:")
    print("   Логин: admin")
    print("   Пароль: admin123")
    print("\n📁 ДАННЫЕ ДЛЯ ТЕСТИРОВАНИЯ:")
    print("   1. CSV файлы созданы в папке")
    print("   2. Для загрузки данных перейдите в 'Загрузить данные'")
    print("   3. Или используйте upload_all.py для автоматической загрузки")
    print("\n🛑 ДЛЯ ОСТАНОВКИ нажмите Ctrl+C в этом окне")
    print("=" * 60)

    try:
        # Ждем пока пользователь не остановит
        flask_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Останавливаю сервер...")
        flask_process.terminate()
    except:
        flask_process.terminate()

    print("\n✅ Сервер остановлен. До свидания!")


if __name__ == "__main__":
    main()