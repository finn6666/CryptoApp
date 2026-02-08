# WSGI entrypoint for production servers (gunicorn)
from app import app

# Common alias used by some WSGI servers
application = app

if __name__ == "__main__":
    app.run()
