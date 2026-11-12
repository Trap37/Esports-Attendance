from flask import Flask, render_template

from server.config import Config, setup_logger
from server.extensions import db, migrate


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    setup_logger()

    from server import models
    from server.routes import register_blueprints

    register_blueprints(app)

    @app.get('/')
    def index():
        return render_template('index.html')

    return app
