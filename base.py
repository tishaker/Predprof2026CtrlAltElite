from flask import Flask, render_template, request, redirect, url_for, send_file
from database.models import db, Applicant
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admission.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'

db.init_app(app)


# Главная страница
@app.route('/')
def index():
    return render_template('index.html')


# Загрузка списков
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        date = request.form['date']
        if file:
            df = pd.read_csv(file)
            # Обработка и сохранение в БД
            # Здесь должна быть логика обновления/добавления/удаления
            for _, row in df.iterrows():
                applicant = Applicant(
                    applicant_id=row['ID'],
                    consent=row['Согласие'],
                    priority=row['Приоритет'],
                    physics_score=row['Физика'],
                    russian_score=row['Русский'],
                    math_score=row['Математика'],
                    achievements_score=row['Достижения'],
                    total_score=row['Сумма'],
                    program=row['Программа'],
                    date=date
                )
                db.session.add(applicant)
            db.session.commit()
            return redirect(url_for('lists'))
    return render_template('upload.html')


# Просмотр списков
@app.route('/lists')
def lists():
    program = request.args.get('program', 'all')
    date = request.args.get('date', 'all')

    query = Applicant.query
    if program != 'all':
        query = query.filter_by(program=program)
    if date != 'all':
        query = query.filter_by(date=date)

    applicants = query.order_by(Applicant.total_score.desc()).all()
    return render_template('lists.html', applicants=applicants)


# Статистика и проходной балл
@app.route('/stats')
def stats():
    # Здесь расчет проходного балла для каждой программы и даты
    # Упрощенный пример
    stats_data = {}
    dates = ['01.08', '02.08', '03.08', '04.08']
    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']

    for prog in programs:
        stats_data[prog] = {}
        for d in dates:
            applicants = Applicant.query.filter_by(program=prog, date=d, consent=True) \
                .order_by(Applicant.total_score.desc()).all()
            # Логика расчета проходного балла
            # ...

    return render_template('stats.html', stats=stats_data)


# Генерация PDF отчета
@app.route('/report/<date>')
def generate_report(date):
    from utils.pdf_report import create_report
    pdf_path = create_report(date)
    return send_file(pdf_path, as_attachment=True)


if __name__ == '__main__':
    if not os.path.exists('admission.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)