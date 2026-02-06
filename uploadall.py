import requests
import os
import time

# ===== НАСТРОЙКИ =====
BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

# Все 16 файлов, которые нужно загрузить
FILES_TO_UPLOAD = [
    ("01.08", "data_01.08_program1.csv"),  # Дата, Имя файла
    ("01.08", "data_01.08_program2.csv"),
    ("01.08", "data_01.08_program3.csv"),
    ("01.08", "data_01.08_program4.csv"),

    ("02.08", "data_02.08_program1.csv"),
    ("02.08", "data_02.08_program2.csv"),
    ("02.08", "data_02.08_program3.csv"),
    ("02.08", "data_02.08_program4.csv"),

    ("03.08", "data_03.08_program1.csv"),
    ("03.08", "data_03.08_program2.csv"),
    ("03.08", "data_03.08_program3.csv"),
    ("03.08", "data_03.08_program4.csv"),

    ("04.08", "data_04.08_program1.csv"),
    ("04.08", "data_04.08_program2.csv"),
    ("04.08", "data_04.08_program3.csv"),
    ("04.08", "data_04.08_program4.csv"),
]


# ===== ФУНКЦИИ =====
def login(session):
    """Вход в систему"""
    print("🔐 Вхожу в систему...")
    login_url = f"{BASE_URL}/login"

    # Сначала GET чтобы получить CSRF токен (если есть)
    session.get(login_url)

    # POST запрос для входа
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "next": "/"  # Куда перенаправить после входа
    }

    response = session.post(login_url, data=login_data, allow_redirects=False)

    if response.status_code == 302:  # Успешный редирект
        print("✅ Вход успешен!")
        return True
    else:
        print(f"❌ Ошибка входа. Код: {response.status_code}")
        # Попробуем просто войти с данными (без CSRF)
        response = session.post(login_url, data=login_data, allow_redirects=True)
        if "Вы успешно вошли" in response.text:
            print("✅ Вход успешен (без CSRF)!")
            return True
        return False


def upload_file(session, date, filename):
    """Загружает один CSV файл"""
    if not os.path.exists(filename):
        print(f"   ⚠️ Файл {filename} не найден, пропускаем")
        return False

    print(f"   📤 Загружаю {filename} за {date}...")

    try:
        with open(filename, 'rb') as f:
            files = {'csv_file': (filename, f, 'text/csv')}
            data = {'date': date}

            response = session.post(f"{BASE_URL}/upload",
                                    files=files,
                                    data=data,
                                    timeout=30)

            if response.status_code == 200:
                if "успешно загружены" in response.text:
                    print(f"   ✅ {filename} — успешно!")
                    return True
                else:
                    print(f"   ❌ {filename} — ошибка в ответе")
                    # Покажем кусочек ошибки
                    error_snippet = response.text[:200] if len(response.text) > 200 else response.text
                    print(f"   Ответ сервера: {error_snippet}")
                    return False
            else:
                print(f"   ❌ {filename} — код ошибки: {response.status_code}")
                return False

    except Exception as e:
        print(f"   ❌ {filename} — исключение: {str(e)}")
        return False


def main():
    """Основная функция"""
    print("=" * 50)
    print("🚀 АВТОМАТИЧЕСКАЯ ЗАГРУЗКА 16 CSV ФАЙЛОВ")
    print("=" * 50)

    # Проверяем, запущен ли сервер
    try:
        test = requests.get(BASE_URL, timeout=2)
        if test.status_code != 200:
            print(f"❌ Сервер не отвечает нормально. Код: {test.status_code}")
            print("   Убедись что app.py запущен на порту 5000")
            return
    except:
        print("❌ Сервер не запущен! Запусти сначала app.py")
        print("   Выполни в другом окне: python app.py")
        return

    # Создаем сессию (сохраняет куки между запросами)
    session = requests.Session()

    # Входим в систему
    if not login(session):
        print("❌ Не удалось войти. Проверь логин/пароль.")
        return

    # Загружаем все файлы
    success_count = 0
    fail_count = 0

    for date, filename in FILES_TO_UPLOAD:
        if upload_file(session, date, filename):
            success_count += 1
        else:
            fail_count += 1

        # Небольшая пауза между запросами
        time.sleep(0.5)

    # Итоги
    print("=" * 50)
    print("📊 ИТОГИ ЗАГРУЗКИ:")
    print(f"   ✅ Успешно: {success_count} файлов")
    print(f"   ❌ Ошибок: {fail_count} файлов")

    if fail_count == 0:
        print("🎉 Все файлы успешно загружены!")
        print(f"   Перейди на {BASE_URL} чтобы проверить данные")
    else:
        print("⚠️ Были ошибки. Проверь:")
        print("   1. Файлы CSV существуют в этой же папке")
        print("   2. В app.py закомментирована строка с delete()")
        print("   3. Столбцы в CSV правильные (ID, Программа и т.д.)")


# ===== ЗАПУСК =====
if __name__ == "__main__":
    main()