# Gunicorn configuration for CryptoApp
import multiprocessing

# Keep the app bound to localhost; expose via Nginx
bind = "127.0.0.1:5001"
# Reasonable default: (2 x $num_cores) + 1
workers = max(2, multiprocessing.cpu_count() * 2 + 1)
worker_class = "gthread"  # good for mixed I/O
threads = 2

# Timeouts
timeout = 60
graceful_timeout = 30
keepalive = 2

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
