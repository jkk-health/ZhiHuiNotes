"""flask run 自动检测入口：python wsgi.py 亦可直接启动。"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
