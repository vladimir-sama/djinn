import webview
from app import app
from multiprocessing import Process, freeze_support


def run_window() -> None:
    webview.create_window('Djinn', 'http://127.0.0.1:5555', False)
    webview.start()

def run_web() -> None:
    app.run('0.0.0.0', 5555, False)

if __name__ == '__main__':
    freeze_support()

    app_web : Process = Process(target=run_web)
    app_web.daemon = True
    app_web.start()

    app_window : Process = Process(target=run_window)
    app_window.start()
    app_window.join()
