import requests
import os
import time

BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

UPLOAD_DIR = "uploads"

FILES_TO_UPLOAD = [
    ("01.08", "data_01.08_program1.csv"),
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


def login(session):
    login_url = f"{BASE_URL}/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD,
        "next": "/"
    }

    response = session.post(login_url, data=data, allow_redirects=True)
    return response.status_code == 200

cleared_dates = set()

def upload_file(session, date, filename):
    filepath = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        print(f"Файл не найден: {filepath}")
        return False

    data = {"date": date}

    if date in cleared_dates:
        data["skip_clear"] = "1"

    with open(filepath, "rb") as f:
        files = {"csv_file": (filename, f, "text/csv")}
        response = session.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data,
            allow_redirects=True
        )

    if response.status_code == 200:
        print(f"Загружено: {filename}")
        cleared_dates.add(date)
        return True

    print(f"Ошибка загрузки: {filename}")
    return False

def main():
    try:
        requests.get(BASE_URL, timeout=2)
    except:
        print("Сервер не запущен")
        return

    session = requests.Session()

    if not login(session):
        print("Не удалось войти")
        return

    success = 0
    for date, filename in FILES_TO_UPLOAD:
        if upload_file(session, date, filename):
            success += 1
        time.sleep(0.1)

    print(f"\nИтого загружено: {success} / {len(FILES_TO_UPLOAD)}")


if __name__ == "__main__":
    main()
