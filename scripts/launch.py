"""Windows 离线启动入口；仅使用标准库准备环境，服务使用独立 demo.db。"""
import argparse
from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "python-runtime" / "python.exe"
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe"
WORK = ROOT / ".tools" / "launcher"
STATE = WORK / "state.json"
HEADER = "X-Zhihui-Launcher-Token"
PORTS = range(5000, 5020)
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def environment():
    env = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "FLASK_DEBUG", "FLASK_ENV"):
        env.pop(name, None)
    cache = ROOT / ".tools" / "cache"
    for name in ("temp", "pip"):
        (cache / name).mkdir(parents=True, exist_ok=True)
    env.update(
        TEMP=str(cache / "temp"), TMP=str(cache / "temp"),
        PIP_CACHE_DIR=str(cache / "pip"), PIP_DISABLE_PIP_VERSION_CHECK="1",
        PIP_NO_INDEX="1", FLASK_DEBUG="0",
        DATABASE_URL="sqlite:///" + (ROOT / "backend" / "demo.db").as_posix(),
    )
    return env


@contextmanager
def startup_lock():
    """双击多次也只进行一次安装和启动；锁随进程结束自动释放。"""
    import msvcrt
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK / "startup.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + 300
        announced = False
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if not announced:
                    print("正在等待前一次启动完成……", flush=True)
                    announced = True
                if time.monotonic() >= deadline:
                    raise RuntimeError("前一次启动仍在进行，请稍后重试。")
                time.sleep(0.2)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def read_state():
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        if (data["port"] not in PORTS or not isinstance(data["token"], str)
                or len(data["token"]) != 64 or not isinstance(data["pid"], int)
                or data["root"] != str(ROOT)):
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def control(data, action="status"):
    url = f'http://127.0.0.1:{data["port"]}/api/_launcher/{action}'
    request = urllib.request.Request(
        url, headers={HEADER: data["token"]},
        data=b"" if action == "stop" else None,
        method="POST" if action == "stop" else "GET",
    )
    with HTTP.open(request, timeout=2) as response:
        return json.load(response)


def running(data):
    if not data:
        return False
    try:
        result = control(data)
        return (result.get("service") == "zhihui-notes-launcher"
                and result.get("pid") == data["pid"]
                and result.get("root") == str(ROOT))
    except (OSError, ValueError, urllib.error.URLError):
        return False


def run_logged(args):
    with (WORK / "startup.log").open("ab") as log:
        result = subprocess.run(
            args, cwd=ROOT, env=environment(), stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    if result.returncode:
        raise RuntimeError(f"环境准备失败（退出码 {result.returncode}）。")


def environment_ready(check_packages=False):
    if not PYTHON.is_file():
        return False
    code = (
        "import sys; from pathlib import Path; "
        f"assert Path(sys.base_prefix).resolve() == Path({str(RUNTIME.parent)!r}).resolve(); "
        "assert sys.version_info[:2] == (3, 11); "
    )
    if check_packages:
        requirements = []
        for line in (ROOT / "backend" / "requirements.txt").read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                requirements.append(tuple(line.strip().split("==", 1)))
        code += (
            "from importlib.metadata import version; "
            f"assert all(version(name) == pinned for name, pinned in {requirements!r}); "
            "import flask, flask_sqlalchemy, markdown, nh3, requests"
        )
    try:
        return subprocess.run(
            [str(PYTHON), "-X", "utf8", "-I", "-c", code], cwd=ROOT,
            env=environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=20, creationflags=subprocess.CREATE_NO_WINDOW,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def prepare():
    if not RUNTIME.is_file():
        raise RuntimeError("缺少便携 Python，请完整解压一键启动版交付包。")
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        raise RuntimeError("缺少网页文件，请完整解压一键启动版交付包。")
    print("[1/3] 检查离线运行环境（首次启动会自动安装，请稍候）……", flush=True)
    if not environment_ready():
        VENV.resolve().relative_to(ROOT)
        run_logged([str(RUNTIME), "-X", "utf8", "-I", "-m", "venv", str(VENV)])
    if not environment_ready(check_packages=True):
        wheels = ROOT / "offline-wheels"
        if not wheels.is_dir():
            raise RuntimeError("缺少 offline-wheels 离线依赖目录。")
        run_logged([
            str(PYTHON), "-X", "utf8", "-I", "-m", "pip", "install", "--no-index",
            "--find-links", str(wheels), "-r", str(ROOT / "backend" / "requirements.txt"),
        ])
        if not environment_ready(check_packages=True):
            raise RuntimeError("后端依赖检查失败，请查看启动日志。")
    print("[2/3] 检查笔记数据库……", flush=True)
    database = ROOT / "backend" / "demo.db"
    if not database.exists():
        pending = WORK / "demo-initializing.db"
        pending.unlink(missing_ok=True)
        run_logged([
            str(PYTHON), "-X", "utf8", str(ROOT / "backend" / "seed.py"),
            "--database", str(pending),
        ])
        if database.exists():
            pending.unlink(missing_ok=True)
        else:
            pending.replace(database)


def show_browser(data, no_browser):
    url = f'http://127.0.0.1:{data["port"]}/login'
    print(f"启动成功：{url}\n演示账号：demo    密码：demo123456", flush=True)
    if not no_browser:
        try:
            if not webbrowser.open(url):
                print("请将上面的地址复制到浏览器打开。", flush=True)
        except OSError:
            print("请将上面的地址复制到浏览器打开。", flush=True)


def start(no_browser=False):
    with startup_lock():
        data = read_state()
        if running(data):
            print("智汇笔记已经运行，正在打开页面。", flush=True)
            show_browser(data, no_browser)
            return
        # 不根据 PID 结束任何进程；只操作带本次随机令牌的服务。
        prepare()
        print("[3/3] 启动服务并等待网页就绪……", flush=True)
        token = secrets.token_hex(32)
        with (WORK / "server.log").open("ab") as log:
            process = subprocess.Popen(
                [str(PYTHON), "-X", "utf8", "-I", str(Path(__file__).resolve()), "serve", token],
                cwd=ROOT, env=environment(), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP),
            )
        deadline = time.monotonic() + 45
        try:
            while time.monotonic() < deadline:
                data = read_state()
                if data and data["token"] == token and running(data):
                    show_browser(data, no_browser)
                    return
                if process.poll() is not None:
                    raise RuntimeError("服务启动失败，请查看服务日志。")
                time.sleep(0.2)
            raise RuntimeError("服务未能在 45 秒内就绪，请查看服务日志。")
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            current = read_state()
            if current and current["token"] == token:
                STATE.unlink(missing_ok=True)
            raise


def stop():
    with startup_lock():
        data = read_state()
        if not data:
            print("智汇笔记尚未启动。", flush=True)
            return
        if not running(data):
            raise RuntimeError("服务没有响应；请查看服务日志。未结束其他进程。")
        control(data, "stop")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not STATE.exists():
                print("智汇笔记已停止，笔记数据已保留。", flush=True)
                return
            time.sleep(0.2)
        raise RuntimeError("服务停止超时，请查看服务日志。")


def serve(token):
    os.environ.update(environment())
    sys.path.insert(0, str(ROOT / "backend"))
    from app import create_app
    from flask import jsonify, request
    import socket
    from werkzeug.serving import ThreadedWSGIServer

    class ExclusiveServer(ThreadedWSGIServer):
        # Windows 的 SO_REUSEADDR 可让两个服务共享同一端口，须使用独占绑定。
        allow_reuse_address = False

        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

    app = create_app(
        DEBUG=False, SQLALCHEMY_DATABASE_URI=os.environ["DATABASE_URL"],
    )

    @app.before_request
    def protect_control():
        if request.path.startswith("/api/_launcher/"):
            if not hmac.compare_digest(request.headers.get(HEADER, ""), token):
                return jsonify(error="Forbidden"), 403

    @app.get("/api/_launcher/status")
    def status():
        return jsonify(service="zhihui-notes-launcher", pid=os.getpid(), root=str(ROOT))

    @app.post("/api/_launcher/stop")
    def shutdown():
        threading.Thread(target=server.shutdown, daemon=True).start()
        return jsonify(status="stopping")

    server = None
    for port in PORTS:
        try:
            server = ExclusiveServer("127.0.0.1", port, app)
            break
        except SystemExit:
            continue
    if server is None:
        raise RuntimeError("5000 至 5019 端口均被占用，请释放一个端口后重试。")
    data = {"port": port, "token": token, "pid": os.getpid(), "root": str(ROOT)}
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp.replace(STATE)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        current = read_state()
        if current and current["token"] == token:
            STATE.unlink(missing_ok=True)


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="智汇笔记离线一键启动")
    parser.add_argument("action", choices=("start", "stop", "serve"), nargs="?", default="start")
    parser.add_argument("token", nargs="?")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "serve":
            if not args.token or len(args.token) != 64:
                raise RuntimeError("缺少服务启动令牌。")
            serve(args.token)
        elif args.action == "stop":
            stop()
        else:
            start(args.no_browser)
        return 0
    except Exception as error:
        print(f"\n操作失败：{error}\n日志目录：{WORK}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
