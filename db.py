from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, unique=False)
    consent = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer)
    physics_score = db.Column(db.Integer)
    russian_score = db.Column(db.Integer)
    math_score = db.Column(db.Integer)
    achievements_score = db.Column(db.Integer)
    total_score = db.Column(db.Integer)
    program = db.Column(db.String(10))
    date = db.Column(db.String(10))

    def __repr__(self):
        return f'<Applicant {self.applicant_id} {self.program} {self.date}>'