from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admission.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('reports', exist_ok=True)


class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer)
    consent = db.Column(db.Boolean)
    priority = db.Column(db.Integer)
    physics = db.Column(db.Integer)
    russian = db.Column(db.Integer)
    math = db.Column(db.Integer)
    achievements = db.Column(db.Integer)
    total = db.Column(db.Integer)
    program = db.Column(db.String(20))
    date = db.Column(db.String(20))

    def __repr__(self):
        return f'<Applicant {self.applicant_id} - {self.program}>'


@app.route('/')
def index():
    dates = db.session.query(Applicant.date).distinct().all()
    dates = [d[0] for d in dates if d[0]]

    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']
    stat = {}

    for prog in programs:
        stat[prog] = {}
        for date in dates:
            count = Applicant.query.filter_by(program=prog, date=date).count()
            consent_count = Applicant.query.filter_by(program=prog, date=date, consent=True).count()
            stat[prog][date] = {'total': count, 'consent': consent_count}

    return render_template('index.html', stats=stat, dates=dates, programs=programs)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        date = request.form.get('date')

        if not file or not date:
            flash('Выберите файл и дату', 'danger')
            return redirect(url_for('upload'))

        try:
            filename = f"{date}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            df = pd.read_csv(filepath)

            Applicant.query.filter_by(date=date).delete()

            for _, row in df.iterrows():
                if 'ID' in df.columns:
                    app_id = int(row['ID'])
                else:
                    continue

                applicant = Applicant(
                    applicant_id=app_id,
                    consent=bool(row.get('Согласие', False)),
                    priority=int(row.get('Приоритет', 1)),
                    physics=int(row.get('Физика', 0)),
                    russian=int(row.get('Русский', 0)),
                    math=int(row.get('Математика', 0)),
                    achievements=int(row.get('Достижения', 0)),
                    total=int(row.get('Сумма', 0)),
                    program=str(row.get('Программа', 'ПМ')),
                    date=date
                )
                db.session.add(applicant)

            db.session.commit()
            flash(f'Данные за {date} успешно загружены!', 'success')

        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')

        return redirect(url_for('index'))

    return render_template('upload.html')


@app.route('/lists')
def lists():
    program = request.args.get('program', 'all')
    date = request.args.get('date', 'all')
    show_consent = request.args.get('consent', 'all')

    query = Applicant.query

    if program != 'all':
        query = query.filter_by(program=program)
    if date != 'all':
        query = query.filter_by(date=date)
    if show_consent == 'yes':
        query = query.filter_by(consent=True)
    elif show_consent == 'no':
        query = query.filter_by(consent=False)

    sort_by = request.args.get('sort_by', 'total')
    order = request.args.get('order', 'desc')

    if sort_by == 'total':
        if order == 'desc':
            applicants = query.order_by(Applicant.total.desc()).all()
        else:
            applicants = query.order_by(Applicant.total.asc()).all()
    elif sort_by == 'id':
        applicants = query.order_by(Applicant.applicant_id).all()
    else:
        applicants = query.all()

    dates = [d[0] for d in db.session.query(Applicant.date).distinct().all() if d[0]]
    programs = [p[0] for p in db.session.query(Applicant.program).distinct().all() if p[0]]

    return render_template('lists.html',
                           applicants=applicants,
                           dates=dates,
                           programs=programs,
                           current_program=program,
                           current_date=date,
                           show_consent=show_consent,
                           now=datetime.now().strftime("%d.%m.%Y %H:%M:%S"))


@app.route('/chart_data')
def chart_data():
    """Возвращает данные для построения графика распределения баллов"""
    program = request.args.get('program', 'all')
    date = request.args.get('date', 'all')
    show_consent = request.args.get('consent', 'all')

    query = Applicant.query

    if program != 'all':
        query = query.filter_by(program=program)
    if date != 'all':
        query = query.filter_by(date=date)
    if show_consent == 'yes':
        query = query.filter_by(consent=True)
    elif show_consent == 'no':
        query = query.filter_by(consent=False)

    applicants = query.all()

    # Собираем баллы для гистограммы
    scores = [app.total for app in applicants]

    if not scores:
        return {
            'labels': [],
            'data': [],
            'average': 0,
            'max_score': 0,
            'min_score': 0,
            'count': 0
        }

    # Создаем интервалы для гистограммы (оптимизировано для скорости)
    min_score = min(scores)
    max_score = max(scores)
    count = len(scores)

    # Быстрый расчет интервалов
    if count < 2:
        return {
            'labels': [f"{int(min_score)}"],
            'data': [count],
            'average': min_score,
            'max_score': max_score,
            'min_score': min_score,
            'count': count
        }

    # Используем фиксированное количество интервалов для скорости
    num_bins = min(10, max(5, count // 10))
    bin_width = (max_score - min_score) / num_bins

    if bin_width == 0:
        return {
            'labels': [f"{int(min_score)}"],
            'data': [count],
            'average': min_score,
            'max_score': max_score,
            'min_score': min_score,
            'count': count
        }

    # Быстрый подсчет
    bins = []
    data = []

    for i in range(num_bins):
        bin_start = min_score + i * bin_width
        bin_end = bin_start + bin_width if i < num_bins - 1 else max_score + 0.1

        # Быстрый подсчет
        count_in_bin = sum(1 for score in scores if bin_start <= score < bin_end)

        if count_in_bin > 0 or i == 0 or i == num_bins - 1:
            label = f"{int(bin_start)}-{int(bin_end)}"
            bins.append(label)
            data.append(count_in_bin)

    return {
        'labels': bins,
        'data': data,
        'average': round(sum(scores) / count, 1),
        'max_score': max_score,
        'min_score': min_score,
        'count': count
    }

@app.route('/passing_scores')
def passing_scores():
    """Расчет проходных баллов на каждую программу"""
    date = request.args.get('date', 'all')

    # Количество мест на каждую программу
    seats = {
        'ПМ': 40,
        'ИВТ': 50,
        'ИТСС': 30,
        'ИБ': 20
    }

    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']
    passing_data = {}

    for prog in programs:
        query = Applicant.query.filter_by(program=prog, consent=True)

        if date != 'all':
            query = query.filter_by(date=date)

        # Получаем всех абитуриентов с согласием, отсортированных по баллам
        applicants = query.order_by(Applicant.total.desc()).all()

        # Рассчитываем проходной балл
        if len(applicants) >= seats[prog]:
            passing_score = applicants[seats[prog] - 1].total
        else:
            passing_score = 'НЕДОБОР'

        # Собираем статистику по приоритетам
        priorities = {1: [], 2: [], 3: [], 4: []}
        for app in applicants:
            if 1 <= app.priority <= 4:
                priorities[app.priority].append(app)

        passing_data[prog] = {
            'seats': seats[prog],
            'total_applicants': len(applicants),
            'passing_score': passing_score,
            'priorities': {
                p: {
                    'count': len(priorities[p]),
                    'scores': [app.total for app in priorities[p][:5]]  # Топ-5 баллов
                }
                for p in range(1, 5)
            }
        }

    return passing_data


@app.route('/priority_cascade')
def priority_cascade():
    """Данные для визуализации каскада приоритетов"""
    program = request.args.get('program', 'all')
    date = request.args.get('date', 'all')

    query = Applicant.query.filter_by(consent=True)

    if program != 'all':
        query = query.filter_by(program=program)
    if date != 'all':
        query = query.filter_by(date=date)

    applicants = query.all()

    # Группируем по ID абитуриента для каскада приоритетов
    applicants_by_id = {}
    for app in applicants:
        if app.applicant_id not in applicants_by_id:
            applicants_by_id[app.applicant_id] = []
        applicants_by_id[app.applicant_id].append(app)

    # Формируем данные для каскада (ограничиваем для производительности)
    cascade_data = []
    for app_id, apps in list(applicants_by_id.items())[:50]:  # Ограничим 50 абитуриентами
        # Сортируем по приоритету
        apps.sort(key=lambda x: x.priority)

        cascade_data.append({
            'id': app_id,
            'priorities': [
                {
                    'program': app.program,
                    'priority': app.priority,
                    'score': app.total,
                    'accepted': False
                }
                for app in apps
            ]
        })

    return {
        'cascade': cascade_data,
        'total_applicants': len(applicants_by_id)
    }




@app.route('/stats')
def stats():
    seats = {'ПМ': 40, 'ИВТ': 50, 'ИТСС': 30, 'ИБ': 20}
    dates = ['01.08', '02.08', '03.08', '04.08']
    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']

    all_applicants = Applicant.query.all()

    stats_data = {}

    for prog in programs:
        stats_data[prog] = {'seats': seats[prog], 'by_date': {}}

    for date in dates:
        all_apps_with_consent = [a for a in all_applicants if a.date == date and a.consent]

        if not all_apps_with_consent:
            for prog in programs:
                stats_data[prog]['by_date'][date] = {
                    'total': 0,
                    'total_consent': 0,
                    'enrolled': 0,
                    'consent_not_enrolled': 0,
                    'passing_score': 'НЕТ ДАННЫХ',
                    'priority_counts': {1: 0, 2: 0, 3: 0, 4: 0},
                    'enrolled_by_priority': {1: 0, 2: 0, 3: 0, 4: 0},
                    'enrolled_list': []
                }
            continue

        applicants_by_id = {}
        for app in all_apps_with_consent:
            if app.applicant_id not in applicants_by_id:
                applicants_by_id[app.applicant_id] = []
            applicants_by_id[app.applicant_id].append(app)

        for app_id, apps in applicants_by_id.items():
            apps.sort(key=lambda x: x.priority)

        sorted_applicant_ids = sorted(
            applicants_by_id.keys(),
            key=lambda aid: (
                max(app.total for app in applicants_by_id[aid]),
                -aid
            ),
            reverse=True
        )

        enrolled = {prog: [] for prog in programs}

        already_enrolled = set()

        for app_id in sorted_applicant_ids:
            apps = applicants_by_id[app_id]

            enrolled_successfully = False
            for app in apps:
                program = app.program
                if len(enrolled[program]) < seats[program]:
                    enrolled[program].append(app)
                    already_enrolled.add(app_id)
                    enrolled_successfully = True
                    break



        for prog in programs:
            enrolled[prog].sort(key=lambda x: x.total, reverse=True)

        for prog in programs:
            if len(enrolled[prog]) >= seats[prog]:
                passing_score = enrolled[prog][seats[prog] - 1].total
            else:
                passing_score = 'НЕДОБОР'
            all_apps_prog = [a for a in all_applicants if a.program == prog and a.date == date]
            priority_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            for app in all_apps_prog:
                if 1 <= app.priority <= 4:
                    priority_counts[app.priority] += 1

            enrolled_by_priority = {1: 0, 2: 0, 3: 0, 4: 0}
            for app in enrolled[prog]:
                if 1 <= app.priority <= 4:
                    enrolled_by_priority[app.priority] += 1

            all_enrolled_ids = set()
            for apps_list in enrolled.values():
                for app in apps_list:
                    all_enrolled_ids.add(app.applicant_id)

            consent_not_enrolled = 0
            for app in all_apps_prog:
                if app.consent and app.applicant_id not in already_enrolled:
                    consent_not_enrolled += 1

            stats_data[prog]['by_date'][date] = {
                'total': len(all_apps_prog),
                'total_consent': len([a for a in all_apps_prog if a.consent]),
                'enrolled': len(enrolled[prog]),
                'consent_not_enrolled': consent_not_enrolled,
                'passing_score': passing_score,
                'priority_counts': priority_counts,
                'enrolled_by_priority': enrolled_by_priority,
                'enrolled_list': enrolled[prog]
            }

    return render_template('stats.html',
                           stats=stats_data,
                           dates=dates,
                           programs=programs)

@app.route('/clear')
def clear_db():
    Applicant.query.delete()
    db.session.commit()
    flash('База данных очищена', 'info')
    return redirect(url_for('index'))


@app.route('/reports')
def reports_page():
    """Страница выбора отчетов"""
    dates = db.session.query(Applicant.date).distinct().all()
    dates = [d[0] for d in dates if d[0]]
    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']
    return render_template('reports.html', dates=dates, programs=programs)


@app.route('/generate_report', methods=['POST'])
def generate_report():
    """Генерация PDF отчета - УПРОЩЕННЫЙ ВАРИАНТ"""
    report_type = request.form.get('report_type')
    program = request.form.get('program', 'all')
    date = request.form.get('date', 'all')

    # Создаем PDF в памяти
    buffer = io.BytesIO()

    # Создаем PDF напрямую через canvas
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4



    # Заголовок отчета
    c.setFont("Helvetica-Bold", 16)

    if report_type == 'summary':
        title = "SUMMARY REPORT"
    elif report_type == 'detailed':
        title = "DETAILED LIST"
    else:
        title = "COMPETITION LISTS"

    c.drawString(100, height - 50, title)

    # Получаем данные
    query = Applicant.query
    if date != 'all':
        query = query.filter_by(date=date)
    if program != 'all':
        query = query.filter_by(program=program)

    applicants = query.order_by(Applicant.total.desc()).all()

    # Простая таблица
    y = height - 100
    c.setFont("Helvetica-Bold", 10)

    # Заголовки таблицы на английском
    headers = ["ID", "PROG", "PRIOR", "PHYS", "RUS", "MATH", "ACHV", "TOTAL", "CONS"]
    col_widths = [30, 30, 30, 30, 30, 30, 30, 30, 30]
    x = 50

    for i, header in enumerate(headers):
        c.drawString(x, y, header)
        x += col_widths[i]

    y -= 20
    c.setFont("Helvetica", 9)

    # Данные
    for app_ in applicants[:30]:  # Ограничим 30 записями
        x = 50
        data = [
            str(app_.applicant_id),
            app_.program,
            str(app_.priority),
            str(app_.physics),
            str(app_.russian),
            str(app_.math),
            str(app_.achievements),
            str(app_.total),
            "Y" if app_.consent else "N"
        ]

        for i, item in enumerate(data):
            c.drawString(x, y, str(item))
            x += col_widths[i]

        y -= 15

        # Новая страница если нужно
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

    # Футер
    c.setFont("Helvetica", 8)
    c.drawString(50, 30, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    c.save()
    buffer.seek(0)

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)