import os
from flask import Flask
from .extensions import db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuration
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'lab_manual.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize Extensions
    db.init_app(app)

    # Register Blueprints
    from .blueprints import main, admin, api
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)

    @app.context_processor
    def inject_experiments():
        try:
            from .models import Experiment
            return {"all_experiments": Experiment.query.all()}
        except Exception:
            return {"all_experiments": []}

    # Create DB Tables
    with app.app_context():
        db.create_all()

    return app
