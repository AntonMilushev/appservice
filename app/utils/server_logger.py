import logging
import os
from datetime import datetime, timedelta
from app.utils.time_utils import sofia_today


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(LOG_DIR, exist_ok=True)


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger("sms_email")
logger.setLevel(logging.INFO)

# Не изпращай тези логове към root logger
logger.propagate = False


# =========================================================
# CUSTOM DAILY FILE HANDLER
# =========================================================

class DailyFileHandler(logging.Handler):

    def __init__(self, log_dir, prefix="sms_email", keep_days=7):
        super().__init__()

        self.log_dir = log_dir
        self.prefix = prefix
        self.keep_days = keep_days

        self.current_date = None
        self.file = None

        self._open_for_today()
        self._cleanup_old_logs()

    def _get_today(self):
     return sofia_today()

    def _get_log_file(self, date_obj):
        filename = f"{self.prefix}_{date_obj.strftime('%Y-%m-%d')}.log"
        return os.path.join(self.log_dir, filename)

    def _open_for_today(self):

        today = self._get_today()

        if self.current_date == today and self.file:
            return

        # Затваряме стария файл
        if self.file:
            try:
                self.file.flush()
                self.file.close()
            except Exception:
                pass

        self.current_date = today

        log_file = self._get_log_file(today)

        self.file = open(
            log_file,
            "a",
            encoding="utf-8"
        )

    def _cleanup_old_logs(self):

        cutoff_date = sofia_today() - timedelta(
        days=self.keep_days
        )

        try:

            for filename in os.listdir(self.log_dir):

                if not filename.startswith(f"{self.prefix}_"):
                    continue

                if not filename.endswith(".log"):
                    continue

                # Очакван формат:
                # sms_email_2026-08-15.log

                date_part = filename[
                    len(self.prefix) + 1:-4
                ]

                try:
                    file_date = datetime.strptime(
                        date_part,
                        "%Y-%m-%d"
                    ).date()

                except ValueError:
                    continue

                if file_date < cutoff_date:

                    file_path = os.path.join(
                        self.log_dir,
                        filename
                    )

                    try:
                        os.remove(file_path)

                    except PermissionError:
                        # Ако файлът е заключен,
                        # просто го пропускаме.
                        pass

                    except Exception:
                        pass

        except Exception:
            pass

    def emit(self, record):

        try:

            today = self._get_today()

            # Ако е нов ден -> отваряме нов файл
            if today != self.current_date:
                self._open_for_today()
                self._cleanup_old_logs()

            message = self.format(record)

            self.file.write(message + "\n")
            self.file.flush()

        except Exception:

            # Не позволявай проблем с логването
            # да събори приложението.
            pass

    def close(self):

        try:

            if self.file:
                self.file.flush()
                self.file.close()
                self.file = None

        except Exception:
            pass

        super().close()


# =========================================================
# FORMAT
# =========================================================

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# HANDLER
# =========================================================

if not logger.handlers:

    handler = DailyFileHandler(
        log_dir=LOG_DIR,
        prefix="sms_email",
        keep_days=7
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)