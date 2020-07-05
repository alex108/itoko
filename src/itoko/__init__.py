import os
import tempfile

from flask import Flask

from itoko.db import db, init_db
from itoko.api import api_blueprint
from itoko.ui import ui_blueprint

__version__ = "0.3.0"


def make_app():
    app = Flask(__name__)
    app.config.update(
        SITE_URL="http://localhost:5000",
        UPLOAD_FOLDER=tempfile.gettempdir(),
        PERMANENT_UPLOAD_FOLDER=tempfile.gettempdir(),
        MAX_CONTENT_LENGTH=256 * 1024 * 1024,
        SECRET_KEY=os.urandom(32),
        SQLITE3_DATABASE="e:\\test.db",
    )
    app.config.from_envvar("ERIO_CABINET_CONFIG", silent=True)

    # Make the uploads folder if it doesn't exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Make the permanent uploads folder if it doesn't exist
    os.makedirs(app.config["PERMANENT_UPLOAD_FOLDER"], exist_ok=True)

    # Add sqlite3 extension
    db.init_app(app)

    # Initialize database
    with app.app_context():
        init_db()

    # Register routes
    app.register_blueprint(api_blueprint)
    app.register_blueprint(ui_blueprint)

    return app


def main():
    app = make_app()
    app.debug = True  # Assume debugging
    app.run()


if __name__ == "__main__":
    main()