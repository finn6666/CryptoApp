# WSGI entrypoint for production servers (gunicorn)
from app import app as application  # common alias used by some WSGI servers

# Also expose as `app` for gunicorn's wsgi:app pattern
from app import app

if __name__ == "__main__":
    app.run()
