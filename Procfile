web: gunicorn -k uvicorn.workers.UvicornWorker -w 2 --timeout 120 -b 0.0.0.0:$PORT src.main:app
