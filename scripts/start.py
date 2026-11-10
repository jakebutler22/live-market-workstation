"""Start both localhost services, verify readiness and stop both on Ctrl-C."""
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def wait_ready(process, url, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited with status {process.returncode}: {url}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(.2)
    raise RuntimeError(f"Server did not become ready within {timeout}s: {url}")


def main():
    python = ROOT / '.venv' / 'bin' / 'python'
    npm = shutil.which('npm')
    if not python.exists() or not (ROOT/'frontend/node_modules/vite').exists() or not npm:
        print('Project dependencies are missing. Follow the installation commands in README.md.',file=sys.stderr)
        return 1
    for port in (8000,5173):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port)) == 0:
                print(f'Port {port} is already in use. If this app is already running, open http://127.0.0.1:5173/; otherwise stop its previous server first.',file=sys.stderr)
                return 1
    processes = []
    def interrupted(signum,frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:
        backend = subprocess.Popen([str(python),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000'],cwd=ROOT)
        processes.append(backend)
        wait_ready(backend,'http://127.0.0.1:8000/api/health')
        frontend = subprocess.Popen([npm,'--prefix','frontend','run','dev','--','--port','5173','--strictPort'],cwd=ROOT)
        processes.append(frontend)
        wait_ready(frontend,'http://127.0.0.1:5173/')
        print('\nWorkstation ready: http://127.0.0.1:5173/\nKeep this terminal running. Ctrl-C stops both servers.\n',flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(.5)
        raise RuntimeError('A workstation server stopped. See its error above.')
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        print(str(exc),file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    sys.exit(main())
