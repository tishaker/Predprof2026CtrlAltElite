import requests
import os
import time

BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

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
    login_data = {"username": USERNAME, "password": PASSWORD, "next": "/"}

    response = session.post(login_url, data=login_data, allow_redirects=False)
    if response.status_code == 302:
        return True

    response = session.post(login_url, data=login_data, allow_redirects=True)
    return "Вы успешно вошли" in response.text


def upload_file(session, date, filename):
    if not os.path.exists(filename):
        return False
    try:
        with open(filename, 'rb') as f:
            files = {'csv_file': (filename, f, 'text/csv')}
            data = {'date': date}

            response = session.post(f"{BASE_URL}/upload",
                                    files=files,
                                    data=data,
                                    timeout=30)

            return response.status_code == 200 and "успешно загружены" in response.text
    except:
        return False


def main():
    try:
        test = requests.get(BASE_URL, timeout=2)
        if test.status_code != 200:
            return
    except:
        return

    session = requests.Session()

    if not login(session):
        return

    success_count = 0
    for date, filename in FILES_TO_UPLOAD:
        if upload_file(session, date, filename):
            success_count += 1
        time.sleep(0.1)
    if success_count == 16:
        print("Данные загружены")

if __name__ == "__main__":
    main()