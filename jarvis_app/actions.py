import shutil
import subprocess


class ActionError(RuntimeError):
    pass


def _open_application_macos(app_name: str) -> None:
    result = subprocess.run(
        ["open", "-a", app_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip() or "unknown error"
        raise ActionError(f"Could not open '{app_name}' on macOS: {details}")


def _open_application_linux(app_name: str) -> None:
    command_like = app_name.lower().replace(" ", "-")
    if shutil.which(command_like):
        subprocess.Popen([command_like], start_new_session=True)
        return
    if shutil.which(app_name):
        subprocess.Popen([app_name], start_new_session=True)
        return
    desktop_id = f"{command_like}.desktop"
    if shutil.which("gtk-launch"):
        result = subprocess.run(["gtk-launch", desktop_id], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return
    raise ActionError(f"Could not open '{app_name}' on Linux.")


def _open_application_windows(app_name: str) -> None:
    script = f"Start-Process -FilePath '{app_name}'"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip() or "unknown error"
        raise ActionError(f"Could not open '{app_name}' on Windows: {details}")


def _close_application_macos(app_name: str) -> None:
    script = f'tell application "{app_name}" to quit'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip() or "unknown error"
        raise ActionError(f"Could not close '{app_name}' on macOS: {details}")


def _close_application_linux(app_name: str) -> None:
    result = subprocess.run(
        ["pkill", "-f", app_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or "").strip() or "process not found"
        raise ActionError(f"Could not close '{app_name}' on Linux: {details}")


def _close_application_windows(app_name: str) -> None:
    escaped = app_name.replace("'", "''")
    script = (
        "$n='" + escaped + "';"
        "$procs=Get-Process | Where-Object { $_.ProcessName -like \"*$n*\" -or $_.MainWindowTitle -like \"*$n*\" };"
        "if(-not $procs){ exit 1 };"
        "$procs | Stop-Process -Force"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip() or "process not found"
        raise ActionError(f"Could not close '{app_name}' on Windows: {details}")
