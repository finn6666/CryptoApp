# Gunicorn configuration for CryptoApp
import multiprocessing

# Keep the app bound to localhost; expose via Nginx
bind = "127.0.0.1:5001"
# Cap at 2 workers for Pi (each loads ML models into memory)
workers = min(2, multiprocessing.cpu_count() + 1)
worker_class = "gthread"  # good for mixed I/O
threads = 2

# Timeouts — agent orchestrator can take up to 120s
timeout = 120
graceful_timeout = 30
keepalive = 2

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
