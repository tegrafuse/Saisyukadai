import os
from flask import Flask
from models import db


def create_app(config_object=None):
    # Use project-level templates directory (project_root/templates)
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=templates_path)
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sns.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Uploads
    upload_folder = os.path.join(app.instance_path, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder

    db.init_app(app)

    with app.app_context():
        from app import routes  # imports views
        app.register_blueprint(routes.bp)
        db.create_all()

    return app
