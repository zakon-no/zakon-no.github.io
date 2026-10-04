"""Локальный сервер сайта.

Делает три вещи одновременно, чтобы не нужно было ничего запускать руками:

1. Отдаёт папку проекта по http://localhost:8080/ — так сайт выглядит ровно
   так же, как в интернете.
2. Следит за index.md, offer.md и build.py. Сохранили файл — index.html
   пересобран автоматически.
3. Встраивает в отдаваемые страницы маленький скрипт: он замечает, что сайт
   пересобран, и обновляет страницу в браузере сам, сохраняя место прокрутки.

Никаких сторонних библиотек: только стандартная библиотека Python 3.9+.
Ничего не пишет в интернет и не выходит за пределы этого компьютера.

Запуск:  python3 serve.py
Остановка: Ctrl + C или кнопка «■» у задачи в VS Code.
"""

import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser

HOST = "127.0.0.1"  # только этот компьютер, не вся сеть
PORT = 8080
ROOT = os.path.dirname(os.path.abspath(__file__))

# Файлы, за которыми следим: сохранили любой — пересобираем.
WATCHED = ("index.md", "offer.md", "build.py")

# Сколько ждём тишины, прежде чем пересобрать: несколько быстрых Cmd+S
# подряд должны дать одну сборку, а не пять.
SETTLE = 0.4

# Как часто страница в браузере спрашивает «не обновилось ли что-нибудь».
POLL_SECONDS = 1.0

# Открывать браузер при запуске. False — открывайте сами, одной кнопкой в VS Code.
OPEN_BROWSER = True

_generation = 0          # растёт при каждой пересборке
_lock = threading.Lock()  # защищает счётчик


def generation():
    with _lock:
        return _generation


def mark_built():
    global _generation
    with _lock:
        _generation += 1
        return _generation


def log(message):
    stamp = time.strftime("%H:%M:%S")
    print("[%s] %s" % (stamp, message), flush=True)


def build(reason):
    """Собирает сайт и показывает результат. Не падает при ошибке в тексте."""
    log("сборка: %s" % reason)
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "build.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    text = (result.stdout or "").strip()
    if result.returncode != 0:
        # Ошибка в index.md — это нормальная ситуация. Сайт на диске остаётся
        # рабочим (прошлой версией), страницу не ломаем.
        for line in (text + "\n" + (result.stderr or "")).splitlines():
            log("  ошибка сборки: %s" % line.strip())
        log("  index.html не изменён. Исправьте index.md и сохраните снова.")
        return False
    for line in text.splitlines():
        if line.strip():
            log("  %s" % line.strip())
    mark_built()
    return True


def snapshot():
    """Время изменения каждого отслеживаемого файла."""
    marks = {}
    for name in WATCHED:
        try:
            marks[name] = os.path.getmtime(os.path.join(ROOT, name))
        except OSError:
            pass
    return marks


def changed_since(before, after):
    return [name for name in after
            if name not in before or before[name] != after[name]]


def outputs_older_than_sources():
    """index.html или offer.html отстали от исходников — пора пересобрать."""
    for source, output in (("index.md", "index.html"), ("offer.md", "offer.html")):
        src = os.path.join(ROOT, source)
        out = os.path.join(ROOT, output)
        if not os.path.exists(out):
            return True
        try:
            if os.path.getmtime(out) < os.path.getmtime(src):
                return True
        except OSError:
            return True
    return False


def watcher():
    """Следит за исходниками и пересобирает сайт. Работает, пока сервер жив."""
    marks = snapshot()
    while True:
        time.sleep(0.25)
        current = snapshot()
        if current == marks:
            continue
        changed = changed_since(marks, current)
        marks = current

        # Ждём, пока вы закончите печатать: несколько быстрых Cmd+S подряд
        # должны дать одну сборку, а не пять.
        quiet_until = time.time() + SETTLE
        while time.time() < quiet_until:
            time.sleep(0.05)
            fresh = snapshot()
            if fresh != marks:
                changed = changed + [n for n in changed_since(marks, fresh) if n not in changed]
                marks = fresh
                quiet_until = time.time() + SETTLE

        build("изменён " + ", ".join(changed))


RELOAD_SCRIPT = """
<script>
(function () {
  var MY = %d;
  var key = "filin-scroll";
  var stored = sessionStorage.getItem(key);
  if (stored !== null) {
    window.scrollTo(0, parseInt(stored, 10) || 0);
    sessionStorage.removeItem(key);
  }
  function check() {
    fetch("/__generated?mine=" + MY, { cache: "no-store" })
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (t.trim() !== String(MY)) {
          sessionStorage.setItem(key, String(window.scrollY));
          location.reload();
        }
      })
      .catch(function () {});
  }
  setInterval(check, %d);
})();
</script>
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    """Обычная раздача файлов + три отличия для удобства и надёжности."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # Запрещаем кэш. Иначе браузер способен показать старый index.html
        # и создать impression, что сайт не обновляется.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # не засоряем вывод задачи каждым запросом картинки

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/__generated":
            body = str(generation()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        name = "index.html" if path in ("/", "") else path.lstrip("/")
        if name.endswith(".html"):
            self.serve_html(name)
            return

        super().do_GET()

    def serve_html(self, name):
        """Отдаёт страницу с добавленным автообновлением.

        Скрипт добавляется только на летом, только при локальном просмотре.
        В index.html на диске его нет — то, что уходит в интернет, чистое.
        """
        path = os.path.join(ROOT, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
        except OSError:
            self.send_error(404, "Файл не найден")
            return

        html = html.replace(
            "</body>",
            (RELOAD_SCRIPT % (generation(), int(POLL_SECONDS * 1000))) + "</body>",
            1,
        )
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


_browser_opened = False


def open_browser_once():
    global _browser_opened
    _browser_opened = True
    webbrowser.open("http://localhost:%d/" % PORT)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    print()
    print("  Сайт: http://localhost:%d/" % PORT)
    print("  Правьте index.md и сохраняйте — страница обновится сама.")
    print("  Остановить: Ctrl+C или кнопка ■ у этой задачи в VS Code.")
    print()

    if outputs_older_than_sources():
        log("index.html отстал от исходников — пересобираю при запуске")
        build("запуск сервера")
    else:
        mark_built()
        log("сайт собран, слежу за изменениями")

    watcher_thread = threading.Thread(target=watcher, daemon=True)
    watcher_thread.start()

    try:
        httpd = Server((HOST, PORT), Handler)
    except OSError as error:
        log("порт %d занят: %s" % (PORT, error))
        log("Похоже, сервер уже запущен в другом окне VS Code.")
        log("Откройте http://localhost:%d/ — он уже работает." % PORT)
        log("Чтобы освободить порт, остановите задачу «Сайт: локальный сервер» "
            "в том окне.")
        return 0

    if OPEN_BROWSER:
        threading.Timer(0.3, open_browser_once).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("остановлено")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
