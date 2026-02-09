# deploy.py - Полный скрипт развертывания
import os
import sys
import subprocess
import time
import sqlite3
from pathlib import Path


def print_step(step, description):
    print(f"\n{'=' * 60}")
    print(f"🚀 {step}")
    print(f"{'=' * 60}")
    print(description)


def check_database():
    """Проверяем наличие и состояние БД"""
    if os.path.exists("admission.db"):
        try:
            conn = sqlite3.connect("admission.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM applicant")
            count = cursor.fetchone()[0]
            conn.close()
            return True, count
        except:
            return False, 0
    return False, 0


def run_command(command, description):
    """Выполняет команду с выводом"""
    print(f"\n▶ {description}")
    print(f"  Команда: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"  ✅ Успешно")
            if result.stdout.strip():
                print(f"  Вывод: {result.stdout[:200]}")
            return True
        else:
            print(f"  ❌ Ошибка: {result.stderr[:200]}")
            return False

    except Exception as e:
        print(f"  ❌ Исключение: {e}")
        return False


def main():
    print("🎯 ЗАПУСК ПОЛНОГО РАЗВЕРТЫВАНИЯ ПРОЕКТА")

    # Шаг 1: Генерация CSV файлов
    print_step("ШАГ 1", "Генерация CSV файлов конкурсных списков")

    if not os.path.exists("csvgen.py"):
        print("❌ Файл csvgen.py не найден!")
        return

    # Проверяем, есть ли уже CSV файлы
    csv_files = list(Path(".").glob("data_*.csv"))
    if len(csv_files) >= 16:
        print(f"✅ Найдено {len(csv_files)} CSV файлов, пропускаем генерацию")
    else:
        if run_command(f"{sys.executable} csvgen.py", "Генерация CSV файлов"):
            # Проверяем результат
            csv_files = list(Path(".").glob("data_*.csv"))
            print(f"✅ Сгенерировано {len(csv_files)} CSV файлов")

            # Быстрая проверка
            for csv_file in csv_files[:3]:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"  {csv_file.name}: {len(lines) - 1} записей")
        else:
            print("❌ Не удалось сгенерировать CSV файлы")
            return

    # Шаг 2: Проверка/очистка базы данных
    print_step("ШАГ 2", "Подготовка базы данных")

    db_exists, record_count = check_database()

    if db_exists:
        print(f"📊 В базе данных: {record_count} записей")
        response = input("  Очистить базу данных? (y/N): ")
        if response.lower() == 'y':
            if run_command(
                    f"{sys.executable} -c \"import sqlite3; conn=sqlite3.connect('admission.db'); conn.execute('DELETE FROM applicant'); conn.commit(); conn.close(); print('База очищена')\"",
                    "Очистка базы данных"):
                print("✅ База данных очищена")
            else:
                print("⚠️  Продолжаем с существующей базой")
    else:
        print("ℹ️ База данных не найдена, будет создана автоматически")

    # Шаг 3: Запуск сервера
    print_step("ШАГ 3", "Запуск Flask сервера")

    # Проверяем, не запущен ли уже сервер
    if run_command("netstat -ano | findstr :5000", "Проверка порта 5000"):
        print("⚠️  Порт 5000 занят. Возможно, сервер уже запущен.")
        response = input("  Попробовать остановить и перезапустить? (y/N): ")
        if response.lower() == 'y':
            run_command("taskkill /F /IM python.exe", "Остановка Python процессов")
            time.sleep(2)

    # Запускаем сервер в фоновом режиме
    print("\n▶ Запуск Flask сервера в фоне...")
    server_process = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Ждем запуска
    print("⏳ Ожидание запуска сервера (5 секунд)...")
    time.sleep(5)

    # Проверяем, запустился ли сервер
    try:
        import requests
        response = requests.get("http://localhost:5000", timeout=3)
        if response.status_code in [200, 302]:
            print("✅ Сервер запущен и отвечает")
        else:
            print(f"⚠️  Сервер отвечает с кодом {response.status_code}")
    except:
        print("❌ Сервер не отвечает. Проверьте вручную:")
        print(f"  Откройте: http://localhost:5000")
        print(f"  Логин: admin | Пароль: admin123")

    # Шаг 4: Загрузка данных
    print_step("ШАГ 4", "Загрузка данных в базу")

    if os.path.exists("uploadall.py"):
        print("⏳ Загрузка CSV файлов в базу данных...")
        time.sleep(2)  # Даем серверу время на полный запуск

        if run_command(f"{sys.executable} uploadall.py", "Загрузка данных через uploadall.py"):
            print("✅ Данные успешно загружены")
        else:
            print("⚠️  Возможно, данные уже загружены или сервер не готов")
    else:
        print("❌ Файл uploadall.py не найден")
        print("ℹ️  Загрузите данные вручную через веб-интерфейс")

    # Шаг 5: Финальная проверка
    print_step("ШАГ 5", "Финальная проверка")

    db_exists, record_count = check_database()
    if db_exists:
        print(f"✅ База данных готова: {record_count} записей")
    else:
        print("⚠️  База данных не создана")

    print("\n" + "=" * 60)
    print("🎉 РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print("\n📌 Дальнейшие действия:")
    print("1. Откройте в браузере: http://localhost:5000")
    print("2. Войдите с: admin / admin123")
    print("3. Проверьте данные на странице 'Конкурсные списки'")
    print("4. Сгенерируйте отчеты в PDF")
    print("\n⚠️  Сервер работает в фоне. Чтобы остановить:")
    print("   - Закройте это окно")
    print("   - Или нажмите Ctrl+C в консоли")
    print("=" * 60)

    # Ожидаем завершения сервера
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервера...")
        server_process.terminate()


if __name__ == "__main__":
    main()