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
                           show_consent=show_consent)


@app.route('/stats')
def stats():
    seats = {
        'ПМ': 40,
        'ИВТ': 50,
        'ИТСС': 30,
        'ИБ': 20
    }

    dates = ['01.08', '02.08', '03.08', '04.08']
    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']

    stats_data = {}

    for prog in programs:
        stats_data[prog] = {
            'seats': seats[prog],
            'by_date': {}
        }

        for date in dates:

            all_apps = Applicant.query.filter_by(program=prog, date=date).all()

            # Только с согласием, отсортированные по баллам
            consent_apps = [app_ for app_ in all_apps if app_.consent]
            consent_apps.sort(key=lambda x: x.total, reverse=True)

            if len(consent_apps) >= seats[prog]:
                passing_score = consent_apps[seats[prog] - 1].total
            else:
                passing_score = 'НЕДОБОР'

            priority_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            for app_ in all_apps:
                if 1 <= app_.priority <= 4:
                    priority_counts[app_.priority] += 1

            stats_data[prog]['by_date'][date] = {
                'total': len(all_apps),
                'consent': len(consent_apps),
                'passing_score': passing_score,
                'priority_counts': priority_counts
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

    # Просто используем стандартные шрифты без кириллицы
    # Будем использовать заглавные латинские буквы для заголовков

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