from datetime import datetime
from .extensions import db
from sqlalchemy.types import JSON

class Experiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(128), nullable=False)
    # Stores the full config: theory, procedure, formulas, constants, I/O schema
    content = db.Column(JSON, nullable=False) 

    def __repr__(self):
        return f'<Experiment {self.title}>'

class StudentRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    student_name = db.Column(db.String(64), nullable=False)
    usn = db.Column(db.String(32), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Store raw input values and computed results for persistence
    inputs = db.Column(JSON, nullable=False)
    results = db.Column(JSON, nullable=False)

    experiment = db.relationship('Experiment', backref=db.backref('runs', lazy=True))

    def __repr__(self):
        return f'<StudentRun {self.student_name} - {self.experiment.slug}>'
