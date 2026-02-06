import csv
import random

PROGRAMS = {
    1: {"name": "ПМИ", "seats": 40},
    2: {"name": "ИВТ", "seats": 50},
    3: {"name": "ИТСС", "seats": 30},
    4: {"name": "ИБ", "seats": 20},
}

D_COUNT = {
    "01.08": {"ПМИ": 60, "ИВТ": 100, "ИТСС": 50, "ИБ": 70},
    "02.08": {"ПМИ": 380, "ИВТ": 370, "ИТСС": 350, "ИБ": 260},
    "03.08": {"ПМИ": 1000, "ИВТ": 1150, "ИТСС": 1050, "ИБ": 800},
    "04.08": {"ПМИ": 1240, "ИВТ": 1390, "ИТСС": 1240, "ИБ": 1190}
}

class Applicant:
    def __init__(self, id):
        self.id = id
        self.applications = {}
        self.physics = random.randint(40, 100)
        self.russian = random.randint(50, 100)
        self.math = random.randint(40, 100)
        self.achievement = random.randint(0, 20)
        self.total = self.physics + self.russian + self.math + self.achievement
        self.has_cons = False

    def add_application(self, program_id, priority):
        self.applications[program_id] = priority

    def to_csv(self, program_id):
        program_names = {1: "ПМ", 2: "ИВТ", 3: "ИТСС", 4: "ИБ"}
        return {
            "ID": self.id,
            "Программа": program_names[program_id],
            "Приоритет": self.applications.get(program_id, 1),
            "Физика": self.physics,
            "Русский": self.russian,
            "Математика": self.math,
            "Достижения": self.achievement,
            "Сумма": self.total,
            "Согласие": 1 if self.has_cons else 0
        }
def save_to_csv(program_id, day_name, applicants):
    filename = f"data_{day_name}_program{program_id}.csv"

    rows = []
    for applicant in applicants:
        if program_id in applicant.applications:
            rows.append(applicant.to_csv(program_id))

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"Создан: {filename}")

def generate_all():
    all_applicants = {}
    next_id = 1000

    for day_name in ['01.08', '02.08', '03.08', '04.08']:
        day_applicants = []

        for program_id in [1, 2, 3, 4]:
            program_name = PROGRAMS[program_id]["name"]
            program_seats = PROGRAMS[program_id]["seats"]
            need_count = D_COUNT[day_name][program_name]

            program_applicants = []

            for applicant in day_applicants:
                if program_id in applicant.applications:
                    program_applicants.append(applicant)

            while len(program_applicants) < need_count:
                if random.random() < 0.4 and len(day_applicants) > 0:
                    applicant = random.choice(day_applicants)
                else:
                    applicant = Applicant(next_id)
                    all_applicants[next_id] = applicant
                    day_applicants.append(applicant)
                    next_id += 1

                if program_id not in applicant.applications:
                    priority = random.randint(1, 4)
                    applicant.add_application(program_id, priority)
                    program_applicants.append(applicant)

            if day_name == "04.08":
                cons_count = 0
                for app in program_applicants:
                    will_cons = random.random() < 0.8
                    app.has_cons = will_cons
                    if will_cons:
                        cons_count += 1

                if cons_count <= program_seats:
                    for app in program_applicants:
                        if not app.has_cons and random.random() < 0.5:
                            app.has_cons = True
                            cons_count += 1
            else:
                for app in program_applicants:
                    app.has_cons = random.random() < 0.3

            save_to_csv(program_id, day_name, program_applicants)

    print("✅ ВСЕ ФАЙЛЫ СОЗДАНЫ!")

if __name__ == "__main__":
    generate_all()