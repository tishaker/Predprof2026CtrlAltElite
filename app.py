from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admission.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('reports', exist_ok=True)


# Модель пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' или 'user'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_user.check_password(current_password):
        flash('Текущий пароль неверен', 'danger')
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash('Новые пароли не совпадают', 'danger')
        return redirect(url_for('profile'))

    current_user.set_password(new_password)
    db.session.commit()
    flash('Пароль успешно изменен', 'success')
    return redirect(url_for('profile'))


# Добавляем защиту для всех маршрутов, требующих авторизации
@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint and not current_user.is_authenticated:
        if request.endpoint not in allowed_routes:
            return redirect(url_for('login', next=request.url))
    return None

@app.route('/')
@login_required
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
@login_required
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

            # Applicant.query.filter_by(date=date).delete()

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
@login_required
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
@login_required
def chart_data():
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

    applicants = Applicant.query.all()

    scores = [app_.total for app_ in applicants]

    if not scores:
        return {
            'labels': [],
            'data': [],
            'average': 0,
            'max_score': 0,
            'min_score': 0,
            'count': 0
        }

    min_score = min(scores)
    max_score = max(scores)
    count = len(scores)

    if count < 2:
        return {
            'labels': [f"{int(min_score)}"],
            'data': [count],
            'average': min_score,
            'max_score': max_score,
            'min_score': min_score,
            'count': count
        }


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


    bins = []
    data = []

    for i in range(num_bins):
        bin_start = min_score + i * bin_width
        bin_end = bin_start + bin_width if i < num_bins - 1 else max_score + 0.1


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
@login_required
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
        for app_ in applicants:
            if 1 <= app_.priority <= 4:
                priorities[app_.priority].append(app_)

        passing_data[prog] = {
            'seats': seats[prog],
            'total_applicants': len(applicants),
            'passing_score': passing_score,
            'priorities': {
                p: {
                    'count': len(priorities[p]),
                    'scores': [app_.total for app_ in priorities[p][:5]]  # Топ-5 баллов
                }
                for p in range(1, 5)
            }
        }

    return passing_data


@app.route('/priority_cascade')
@login_required
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
    for app_ in applicants:
        if app_.applicant_id not in applicants_by_id:
            applicants_by_id[app_.applicant_id] = []
        applicants_by_id[app_.applicant_id].append(app_)

    # Формируем данные для каскада (ограничиваем для производительности)
    cascade_data = []
    for app_id, apps in list(applicants_by_id.items())[:50]:  # Ограничим 50 абитуриентами
        # Сортируем по приоритету
        apps.sort(key=lambda x: x.priority)

        cascade_data.append({
            'id': app_id,
            'priorities': [
                {
                    'program': app_.program,
                    'priority': app_.priority,
                    'score': app_.total,
                    'accepted': False
                }
                for app_ in apps
            ]
        })

    return {
        'cascade': cascade_data,
        'total_applicants': len(applicants_by_id)
    }


@app.route('/stats')
@login_required
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
        for app_ in all_apps_with_consent:
            if app_.applicant_id not in applicants_by_id:
                applicants_by_id[app_.applicant_id] = []
            applicants_by_id[app_.applicant_id].append(app_)

        for app_id, apps in applicants_by_id.items():
            apps.sort(key=lambda x: x.priority)

        sorted_applicant_ids = sorted(
            applicants_by_id.keys(),
            key=lambda aid: (
                max(app__.total for app__ in applicants_by_id[aid]),
                -aid
            ),
            reverse=True
        )

        enrolled = {prog: [] for prog in programs}
        already_enrolled = set()

        for app_id in sorted_applicant_ids:
            apps = applicants_by_id[app_id]

            for app_ in apps:
                program = app_.program
                if len(enrolled[program]) < seats[program]:
                    enrolled[program].append(app_)
                    already_enrolled.add(app_id)
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
            for app_ in all_apps_prog:
                if 1 <= app_.priority <= 4:
                    priority_counts[app_.priority] += 1

            enrolled_by_priority = {1: 0, 2: 0, 3: 0, 4: 0}
            for app_ in enrolled[prog]:
                if 1 <= app_.priority <= 4:
                    enrolled_by_priority[app_.priority] += 1

            all_enrolled_ids = set()
            for apps_list in enrolled.values():
                for app_ in apps_list:
                    all_enrolled_ids.add(app_.applicant_id)

            consent_not_enrolled = 0
            for app_ in all_apps_prog:
                if app_.consent and app_.applicant_id not in already_enrolled:
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
@login_required
def clear_db():
    Applicant.query.delete()
    db.session.commit()
    flash('База данных очищена', 'info')
    return redirect(url_for('index'))


@app.route('/reports')
@login_required
def reports_page():
    """Страница выбора отчетов"""
    dates = db.session.query(Applicant.date).distinct().all()
    dates = [d[0] for d in dates if d[0]]
    programs = ['ПМ', 'ИВТ', 'ИТСС', 'ИБ']
    return render_template('reports.html', dates=dates, programs=programs)


@app.route('/generate_report', methods=['POST'])
@login_required
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


# Функция для создания первого пользователя (администратора)
def create_admin_user():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin123')  # Сменить в продакшене!
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: username='admin', password='admin123'")



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
    app.run(debug=True, port=5000)