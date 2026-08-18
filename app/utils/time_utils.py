import pytz
from datetime import datetime

SOFIA_TZ = pytz.timezone("Europe/Sofia")


def sofia_now():
    """
    Връща ТЕКУЩОТО време в София като НАИВЕН datetime (без tzinfo).

    Защо наивен: всички start_time/end_time в базата се пазят без tzinfo
    и представляват локално софийско време (изпратено директно от браузъра
    на клиента/барбъра). Ако сървърът работи на UTC (обичайно за Frankfurt
    cloud инстанции), 'datetime.now()' и 'datetime.utcnow()' връщат различно
    от реалното софийско време — с тази функция навсякъде сравняваме
    еднакви неща.
    """
    return datetime.now(SOFIA_TZ).replace(tzinfo=None)


def sofia_today():
    return sofia_now().date()