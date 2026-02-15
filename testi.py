from app import app, db, Applicant

with app.app_context():
    first = Applicant.query.first()
    print(first.consent)
    print(type(first.consent))
