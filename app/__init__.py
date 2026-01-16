import os
from flask import Flask
from models import db


def create_app(config_object=None):
    # Use project-level templates directory (project_root/templates)
    templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    # Serve project-level static folder (project_root/static)
    static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    app = Flask(__name__, template_folder=templates_path, static_folder=static_path, static_url_path='/static')
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sns.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Uploads
    upload_folder = os.path.join(app.instance_path, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder

    db.init_app(app)

    from datetime import datetime, timezone

    def time_ago(dt):
        if not dt:
            return ''
        # Handle naive datetimes as UTC for simplicity
        if dt.tzinfo is None:
            now = datetime.utcnow()
        else:
            now = datetime.now(timezone.utc)
            dt = dt.astimezone(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"{seconds}秒前"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}分前"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}時間前"
        days = hours // 24
        if days < 7:
            return f"{days}日前"
        weeks = days // 7
        if weeks < 5:
            return f"{weeks}週間前"
        months = days // 30
        if months < 12:
            return f"{months}か月前"
        years = days // 365
        return f"{years}年前"

    with app.app_context():
        from app import routes  # imports views
        app.register_blueprint(routes.bp)
        db.create_all()

        # NOTE: Schema changes are intentionally not applied automatically.
        # If you add/remove columns, run migrations manually with your preferred tool.

    # Jinja filter
    app.jinja_env.filters['time_ago'] = time_ago

    return app
