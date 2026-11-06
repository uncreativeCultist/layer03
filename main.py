import time
import selenium
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from pathlib import Path
import json
import tkinter as tk
import shutil
import hashlib
from utils.logger import setup_logging
from utils.version import app_version
from tkinter import messagebox
import sys
import multiprocessing
import os
import threading
from urllib.parse import unquote
import ctypes
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
)
from PyQt6.QtCore import QTimer, QMetaObject, Qt, Q_ARG
from core.steam_helpers import _find_steam_windows
import webbrowser
import subprocess

logger = setup_logging()

logger.info("========================================")
logger.info(f"ACCELA {app_version} starting...")
logger.info("========================================")

if sys.platform == "win32":
    steam_path = _find_steam_windows()
    def resource_path(relative_path):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).resolve().parent

        return base_path / relative_path

    if not Path(f"{steam_path}/user32.dll").exists():
        shutil.copyfile(resource_path('deps/GreenLuma/user32.dll'), f'{steam_path}/user32.dll')
    else:
        localglhash = hashlib.md5(open(resource_path('deps/GreenLuma/user32.dll'),'rb').read()).hexdigest()
        if not hashlib.md5(open(F'{steam_path}/user32.dll','rb').read()).hexdigest() == localglhash:
            os.remove(f'{steam_path}/user32.dll')
            shutil.copyfile(resource_path('deps/GreenLuma/user32.dll'), f'{steam_path}/user32.dll')
            logger.info("Replaced current GreenLuma installation with local.")

    if not Path(f"{steam_path}/AppList/").exists():
            shutil.copytree(resource_path('deps/GreenLuma/AppList/'), f"{steam_path}/AppList/")
    if not Path(f"{steam_path}/AppList/AppList.ini").exists():
            shutil.copyfile(resource_path('deps/GreenLuma/AppList/AppList.ini'), f"{steam_path}/AppList/AppList.ini")
    #sys.exit(1)

def getnewKey():

    driver = webdriver.Chrome()
    driver.minimize_window()
    driver.get("https://hubcapmanifest.com/.well-known/security.txt") # probably smallest page

    try:
        try:
            with open("hubcapsesh.json", "r") as file:
                cookies = json.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
            driver.delete_cookie("csrf_token")
            driver.refresh()
        except FileNotFoundError:
                driver.quit()
                driver = webdriver.Chrome()
                driver.get("https://hubcapmanifest.com/auth/discord")
                WebDriverWait(driver, timeout=120).until(
                        EC.any_of(
                            lambda d: d.get_cookie('session') is not None,
                            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "You must be a member of our Discord server")
                        )
                    )
                    
                cookie = driver.get_cookie('session')
                if cookie:
                    session = cookie['value']
                    cookies = driver.get_cookies()
                    with open("hubcapsesh.json", "w+") as file:
                        json.dump(cookies, file)
                        driver.minimize_window()
                else:
                    driver.quit()
                    logger.warning("Authentication Failed: Please make sure you've joined discord.gg/hubcapsmanifest, and have verified your account.")
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes("-topmost", True)
                    root.lift()
                    root.focus_force()
                    messagebox.showerror("Authentication Failed", "Please make sure you've joined discord.gg/hubcapsmanifest, and have verified your account.")
                    sys.exit(1)

        driver.get("https://hubcapmanifest.com/api-keys/stats")
            
        cookies = driver.get_cookies()
        with open("hubcapsesh.json", "w+") as file:
            json.dump(cookies, file)
        driver.get("https://hubcapmanifest.com/api-keys/stats")
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'enerate Key')]"))  
        )
        try:
            button.click()
        except selenium.common.exceptions.ElementClickInterceptedException:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            logger.warning("Authentication Failed: Please make sure you've joined the hubcapsmanifest Discord server, and have verified your account.")
            messagebox.showerror("Authentication Failed", "Please make sure you've joined the hubcapsmanifest Discord server, and have verified your account.")
            sys.exit(1)

        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Generate']"))  
        )
        button.click()
        element = WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.XPATH, "//*[starts-with(., 'smm_')]")
        )
        api_key = element.text.splitlines()[0].strip()
        try:
            with open("hubcapkey.txt", "w") as f:
                f.write(api_key)
        except:
            return

    finally:
        driver.quit()
if Path("hubcapkey.txt").exists():
    logger.info("Key found, validating...")
    api_key = open("hubcapkey.txt").read()

    try:
        response = requests.get(f'https://hubcapmanifest.com/api/v1/user/stats?api_key={api_key}')
        if "API key not found or expired" in response:
            logger.info("Key is invalid, getting new one...")
            getnewKey()
        else:
            logger.info("Key appears to be valid, continuing...")
    except:
        logger.info("Key is invalid, getting new one...")
        getnewKey()

else:
    getnewKey()

api_key = open("hubcapkey.txt").read()

from ui.main_window import MainWindow
from ui.theme import update_appearance
from managers.cli_manager import run_cli_mode, open_cli_terminal
from utils.settings import get_settings
from utils.yaml_config_manager import (
    backup_config_on_startup,
    ensure_slssteam_api_enabled,
    get_user_config_path,
)
from core.steam_helpers import fix_greenluma_offline_mode
from core.morrenus_api import download_manifest
from utils.helpers import create_font_from_settings

# -----------------------------------------------------------------------------
# Platform-specific adjustments
# -----------------------------------------------------------------------------
def set_app_user_model_id():
    """Set the AppUserModelID for Windows to ensure correct taskbar grouping."""
    if sys.platform == "win32":
        try:
            my_app_id = "god.is.in.the.wired.accela"
            # noinspection PyUnresolvedReferences
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
        except (ImportError, AttributeError):
            pass  # Fails gracefully on non-Windows platforms or if ctypes is missing


set_app_user_model_id()

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():

    # People only have substance within the memories of other people.

    app = QApplication(sys.argv)

    # -------------------------------------------------------------------------
    # Argument Parsing
    # -------------------------------------------------------------------------
    cli_mode = False
    command_line_zips = []
    command_line_appid = None

    def _add_zip_from_url(zip_url: str, found_suffix: str = "") -> bool:
        if not zip_url:
            return False
        if os.path.exists(zip_url):
            command_line_zips.append(zip_url)
            suffix = f" {found_suffix}" if found_suffix else ""
            logger.info(f"Found ZIP file from URL: {zip_url}{suffix}")
            return True
        logger.warning(f"ZIP file not found from URL: {zip_url}")
        return False

    def _parse_url_action(url: str):
        nonlocal cli_mode, command_line_appid
        try:
            url_content = url[9:]  # Remove 'accela://'
            if url_content.startswith("cli/"):
                cli_mode = True
                rest = url_content[4:]
            else:
                rest = url_content

            if "/" in rest:
                action, param_val = rest.split("/", 1)
                param_val = unquote(param_val)
            else:
                action = rest
                param_val = None

            if action == "download" and param_val and param_val.isdigit():
                command_line_appid = int(param_val)
                mode_str = "CLI" if cli_mode else "GUI"
                logger.info(
                    f"Found accela://{action} URL for AppID: {param_val} ({mode_str} mode)"
                )
            elif action == "zip" and param_val:
                _add_zip_from_url(param_val, "(GUI mode)" if not cli_mode else "")
            else:
                logger.warning(f"Invalid accela:// URL format: {url}")
        except ValueError as ve:
            logger.error(f"Failed to parse URL {url}: {ve}")

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-cli", "--cli"):
            cli_mode = True
        elif arg == "--appid" and i + 1 < len(args):
            appid_str = args[i + 1]
            if appid_str.isdigit():
                command_line_appid = int(appid_str)
            else:
                logger.error(f"Invalid AppID: {appid_str} (must be a number)")
            i += 1
        elif arg.startswith("accela://"):
            _parse_url_action(arg)
        elif arg.lower().endswith(".zip"):
            zip_file_path = os.path.abspath(arg)
            if os.path.exists(zip_file_path):
                command_line_zips.append(zip_file_path)
                logger.info(f"Found ZIP file from command line: {zip_file_path}")
            else:
                logger.warning(f"ZIP file not found: {arg}")
        i += 1

    if command_line_appid and command_line_zips:
        logger.error("Cannot use --appid and .zip files together. Choose one.")
        return None

    # -------------------------------------------------------------------------
    # CLI Mode Execution
    # -------------------------------------------------------------------------
    if cli_mode and (command_line_zips or command_line_appid):
        if cli_mode and sys.platform == "linux":
            if command_line_appid:
                logger.info(
                    f"Opening CLI mode in external terminal for AppID {command_line_appid}"
                )
                if open_cli_terminal(appid=command_line_appid):
                    return None
            elif command_line_zips:
                logger.info("Opening CLI mode in external terminal for ZIP(s)")
                if open_cli_terminal(zip_path=command_line_zips[0]):
                    return None

        if command_line_appid:
            logger.info(f"Will process AppID {command_line_appid} via CLI")
            return run_cli_mode(app, None, logger, appid=command_line_appid)
        else:
            logger.info(f"Processing {len(command_line_zips)} ZIPs via CLI")
            return run_cli_mode(app, command_line_zips, logger)

    # -------------------------------------------------------------------------
    # GUI Mode Initialization
    # -------------------------------------------------------------------------

    config_path = get_user_config_path()
    try:
        backup_created = backup_config_on_startup(config_path)
        if backup_created:
            logger.info("SLSsteam config backup created at startup")

        if config_path.exists():
            if ensure_slssteam_api_enabled(config_path):
                logger.info("SLSsteam API enabled in config")
    except OSError as e:
        logger.error(f"Startup I/O error (Config/Backup): {e}")

    # 2. Settings & Theme
    settings = get_settings()
    accent_color = settings.value("accent_color", "#C06C84")
    bg_color = settings.value("background_color", "#000000")
    ui_mode = settings.value("ui_mode", "default")

    font_file = None
    font_to_use = QFont()

    if ui_mode == "sonic":
        accent_color = "#ffcc00"
        bg_color = "#002c83"
        font_file = settings.value("font-file", "sonic/sonic-1-hud-font.otf")
    else:
        font_to_use = create_font_from_settings(settings)

    # 3. GreenLuma Check
    try:
        fix_greenluma_offline_mode()
    except OSError as e:
        logger.warning(f"Failed to check GreenLuma status: {e}")

    # 4. Apply Appearance
    font_ok, font_info = update_appearance(
        app, accent_color, bg_color, font=font_to_use, font_file=font_file
    )
    if font_ok:
        logger.info(f"Loaded custom font: '{str(font_info)}'")
    else:
        logger.warning(f"Failed to load custom font: '{str(font_info)}'")

    # -------------------------------------------------------------------------
    # Main Window Launch
    # -------------------------------------------------------------------------
    try:
        main_win = MainWindow()
        main_win.show()
        logger.info("Main window displayed successfully.")

        if settings.value("update", True) == True:
            update_url = requests.get("https://raw.githubusercontent.com/uncreativeCultist/layer03/refs/heads/main/res/version")
            if update_url.status_code == 200:
                latestver = update_url.text
                if app_version not in latestver:
                    if "dev" not in app_version.lower():
                        logger.warning("You have 1 unread mail.")
                        msg_box = QMessageBox()
                        msg_box.setWindowTitle("Outdated Version")
                        msg_box.setText(
                            "An update is available.\n"
                            f"You are running {app_version}, while the latest is\n {latestver}.\n\n"
                            "Press 'Apply' to update, or press ignore.\n"
                            "You can turn off update notifications in settings."
                        )
                        msg_box.setStandardButtons(QMessageBox.StandardButton.Apply)
                        msg_box.addButton(QMessageBox.StandardButton.Ignore)
                        msg_box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                        reply = msg_box.exec()
                        if reply == QMessageBox.StandardButton.Apply:
                            if sys.platform == "linux" or "darwin":
                                subprocess.run(["git", "pull"], capture_output=True, text=True)
                                subprocess.run(["./venv/bin/python3", "-m", "pip", "install", "-r", "requirements.txt"], capture_output=True, text=True)
                                msg_box = QMessageBox()
                                msg_box.setWindowTitle("Update installed")
                                msg_box.setText(
                                    f"Update installed. ACCELA will now close."
                                )
                                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                                msg_box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                                msg_box.exec()
                                sys.exit(1)
                            else:
                                webbrowser.open("https://github.com/uncreativeCultist/layer03/releases/")
                            sys.exit(1)


        # ---------------------------------------------------------------------
        # Post-Launch Processing
        # ---------------------------------------------------------------------
        if command_line_zips or command_line_appid:

            def threaded_manifest_download(appid):
                """Background thread to handle network I/O."""
                try:
                    logger.info(
                        f"Downloading manifest for AppID {appid} (Background Thread)"
                    )
                    zip_file, error = download_manifest(appid)
                    if error:
                        logger.error(f"Failed to download manifest: {error}")
                        return

                    # Schedule the UI update on the main thread
                    # We use QMetaObject.invokeMethod to safely cross thread boundaries
                    QMetaObject.invokeMethod(
                        main_win,
                        "add_job_safely",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, zip_file),
                    )
                except Exception as ex:
                    logger.error(f"Threaded download failed: {ex}")

            def process_command_line_args():
                """Dispatcher for command line args."""
                if command_line_appid:
                    t = threading.Thread(
                        target=threaded_manifest_download,
                        args=(command_line_appid,),
                        daemon=True,
                    )
                    t.start()
                else:
                    logger.info(f"Adding {len(command_line_zips)} ZIP file(s) to queue")
                    for zip_file in command_line_zips:
                        main_win.job_queue.add_job(zip_file)

            def add_job_safely_patch(path):
                logger.info(f"Adding to queue: {os.path.basename(path)}")
                main_win.job_queue.add_job(path)

            # Monkey-patching the method onto the instance for safety
            main_win.add_job_safely = add_job_safely_patch

            QTimer.singleShot(0, process_command_line_args)

        sys.exit(app.exec())
    except Exception as e:
        logger.critical(
            f"A critical error occurred. Error: {e}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
