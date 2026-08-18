/* =========================================================
   GLOBAL STATE
   ========================================================= */

let selectedBarber = null; // пази избрания бръснар


/* =========================================================
   BARBER SELECTION
   ========================================================= */

function selectBarber(e, id) {
    document.querySelectorAll('.barber-card')
        .forEach(c => c.classList.remove('active'));

    e.currentTarget.classList.add('active');

    selectedBarber = id;

    // unlock booking
    document.getElementById('bookingSection')
        .classList.remove('disabled');

    // remove lock overlay
    const lock = document.querySelector('.booking-lock');
    if (lock) lock.remove();

    // 👉 scroll към дата (само това!)
    document.getElementById('date').scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });
}

function goHome() {
    // scroll до горе
    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    // reset selection (barber, service, slot)
    document.querySelectorAll(".active").forEach(el => {
        el.classList.remove("active");
    });

    // disable booking секцията
    document.getElementById("bookingSection").classList.add("disabled");

    // clear inputs (по желание, но силно препоръчвам)
    document.getElementById("name").value = "";
    document.getElementById("phone").value = "";
    document.getElementById("email").value = "";

    // clear selected values
    document.getElementById("service").value = "";
    document.getElementById("selectedTime").value = "";

    // clear slots
    document.getElementById("slots").innerHTML = "";

    // reset summary
    document.getElementById("summary").classList.add("hidden");
}


/* =========================================================
   LOAD AVAILABLE SLOTS (API CALL)
   ========================================================= */

function loadSlots() {
    const date = document.getElementById("date").value;
    const service = document.getElementById("service").value;

    if (!selectedBarber || !date || !service) return;

    const container = document.getElementById("slots");
    container.innerHTML = "<p>Зареждане...</p>";

    fetch(`/availability?barber_id=${selectedBarber}&date=${date}&service_id=${service}`)
        .then(r => r.json())
        .then(slots => {
            container.innerHTML = "";

            if (!Array.isArray(slots) || slots.length === 0) {
                container.innerHTML = "<p>Няма свободни часове</p>";
                return;
            }

            document.getElementById("selectedTime").value = "";
            document.getElementById("summary").classList.add("hidden");

            slots.forEach(time => {
                const btn = document.createElement("button");
                btn.textContent = time;
                btn.classList.add("slot");

                btn.onclick = () => selectSlot(btn, time);

                container.appendChild(btn);
            });
        })
        .catch(err => {
            console.error("ERROR:", err);
            container.innerHTML = "<p>Грешка при зареждане</p>";
        });
}


/* =========================================================
   SLOT SELECTION
   ========================================================= */

function selectSlot(element, time) {
    document.querySelectorAll(".slot")
        .forEach(s => s.classList.remove("active"));

    element.classList.add("active");

    document.getElementById("selectedTime").value = time;

    // 👉 scroll към формата
    document.getElementById('name').scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });

    updateSummary();
    checkForm();
}


/* =========================================================
   BOOKING REQUEST (POST)
   ========================================================= */

function book() {
    const name = document.getElementById("name").value;
    const phone = document.getElementById("phone").value;
    const email = document.getElementById("email").value;
    const service = document.getElementById("service").value;
    const date = document.getElementById("date").value;
    const time = document.getElementById("selectedTime").value;

    const btn = document.querySelector(".main-btn");

    const consent = document.getElementById("consent").checked;

    // 🔒 GDPR check
    if (!consent) {
        showError("Трябва да се съгласите с обработката на лични данни.");
        return;
    }

    // loading state
    btn.disabled = true;
    btn.innerText = "Запазване...";

    fetch('/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({
            name,
            phone,
            email,
            consent,
            barber_id: selectedBarber,
            service_id: service,
            appointment_time: `${date}T${time}:00`
        })
    })
        .then(async r => {
            let data;

            try {
                data = await r.json();
            } catch {
                throw new Error("Сървърна грешка");
            }

            if (!r.ok) {
                throw new Error(data.error || "Грешка");
            }

            return data;
        })
        .then(res => {
            showSuccess();
            loadSlots();

            document.getElementById("name").value = "";
            document.getElementById("phone").value = "";
            document.getElementById("email").value = "";
            document.getElementById("selectedTime").value = "";

            btn.disabled = false;
            btn.innerText = "Запази";
        })
        .catch(err => {
            console.error("BOOK ERROR:", err);

            btn.disabled = false;
            btn.innerText = "Запази";

            // ✅ само едно съобщение
            showError(err.message);
        });
}


/* =========================================================
   SUMMARY UI
   ========================================================= */

function updateSummary() {
    document.getElementById("summary").classList.remove("hidden");

    document.getElementById("sumBarber").innerText =
        document.querySelector(".barber-card.active p")?.innerText || "-";

    document.getElementById("sumService").innerText =
        document.querySelector(".service-card.active p")?.innerText || "-";

    document.getElementById("sumDate").innerText =
        document.getElementById("date").value;

    document.getElementById("sumTime").innerText =
        document.getElementById("selectedTime").value || "-";
}


/* =========================================================
   FORM VALIDATION
   ========================================================= */

function checkForm() {
    const name = document.getElementById("name").value;
    const phone = document.getElementById("phone").value;
    const time = document.getElementById("selectedTime").value;
    const consent = document.getElementById("consent").checked;

    const btn = document.querySelector(".main-btn");

    if (name && phone && time && selectedBarber && consent) {
        btn.disabled = false;
        btn.style.opacity = "1";
    } else {
        btn.disabled = true;
        btn.style.opacity = "0.5";
    }
}

/* =========================================================
   INPUT LISTENERS
   ========================================================= */

document.getElementById("name").addEventListener("input", checkForm);
document.getElementById("phone").addEventListener("input", checkForm);
document.getElementById("consent").addEventListener("change", checkForm);


/* =========================================================
   SUCCESS MODAL
   ========================================================= */

function showSuccess() {
    const modal = document.getElementById("successModal");

    modal.classList.remove("hidden");

    setTimeout(() => {
        modal.classList.add("hidden");
    }, 2500);
}

function closeModal() {
    document.getElementById("successModal").classList.add("hidden");
}

// click outside modal
document.getElementById("successModal").addEventListener("click", function (e) {
    if (e.target === this) closeModal();
});

// ESC close
document.addEventListener("keydown", function (e) {
    const modal = document.getElementById("successModal");

    if (e.key === "Escape" && !modal.classList.contains("hidden")) {
        closeModal();
    }
});


/* =========================================================
   DATE PICKER (Flatpickr)
   ========================================================= */

// отваря календара при focus
document.getElementById("date").addEventListener("focus", function () {
    this._flatpickr.open();
});


/* =========================================================
   SERVICE SELECTION
   ========================================================= */

function selectService(e, id) {
    document.querySelectorAll('.service-card')
        .forEach(c => c.classList.remove('active'));

    e.currentTarget.classList.add('active');

    document.getElementById("service").value = id;

    // 👉 scroll към часовете
    document.getElementById('slots').scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });

    // 👉 зарежда слотове (ако има всичко нужно)
    loadSlots();

    updateSummary();
    checkForm();
}



/* =========================================================
   NAVIGATION & SCROLL
   ========================================================= */

// scroll до booking
function goToBooking() {
    const selected = document.querySelector('.barber-card.active');
    const barbersSection = document.getElementById('barbersSection');
    const bookingSection = document.getElementById('bookingSection');

    if (!selected) {
        barbersSection.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });

        // визуален hint
        barbersSection.classList.add('highlight');

        setTimeout(() => {
            barbersSection.classList.remove('highlight');
        }, 1500);

    } else {
        bookingSection.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// navbar scroll effect
window.addEventListener("scroll", () => {
    const nav = document.querySelector(".navbar");

    if (window.scrollY > 30) {
        nav.classList.add("scrolled");
    } else {
        nav.classList.remove("scrolled");
    }
});

const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

flatpickr("#date", {
    defaultDate: "today",
    dateFormat: "Y-m-d",
    minDate: "today",

    locale: {
        firstDayOfWeek: 1,
        weekdays: {
            shorthand: ["Нед", "Пон", "Вт", "Ср", "Чет", "Пет", "Съб"],
            longhand: [
                "Неделя", "Понеделник", "Вторник",
                "Сряда", "Четвъртък", "Петък", "Събота"
            ]
        },
        months: {
            shorthand: ["Ян", "Фев", "Мар", "Апр", "Май", "Юни", "Юли", "Авг", "Сеп", "Окт", "Ное", "Дек"],
            longhand: [
                "Януари", "Февруари", "Март", "Април", "Май", "Юни",
                "Юли", "Август", "Септември", "Октомври", "Ноември", "Декември"
            ]
        }
    },

    altInput: true,
    altFormat: "l, d F Y",
    disableMobile: true, // 🔥 ключово

    onChange: function (selectedDates, dateStr) {
        const selectedDate = selectedDates[0];

        let day = selectedDate.toLocaleDateString("bg-BG", {
            weekday: "long"
        });

        day = day.charAt(0).toUpperCase() + day.slice(1);

        const formatted = selectedDate.toLocaleDateString("bg-BG", {
            year: "numeric",
            month: "long",
            day: "numeric"
        });

        document.getElementById("sumDay").innerText = day;
        document.getElementById("sumDate").innerText = formatted;

        document.querySelector('.services').scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });

        loadSlots();
    }
});

const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add("show");

            const counters = entry.target.querySelectorAll(".counter");
            counters.forEach(counter => {
                if (!counter.classList.contains("started")) {
                    counter.classList.add("started");
                    animateCounter(counter);
                }
            });
        }
    });
}, { threshold: 0.35 });

document.querySelectorAll(".animate").forEach(el => {
    observer.observe(el);
});

function animateCounter(el) {
    const target = +el.getAttribute("data-target");
    const duration = 1200; // ms
    const startTime = performance.now();

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function update(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = easeOutCubic(progress);

        const value = Math.floor(eased * target);
        el.innerText = value;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.innerText = target;

            // 🔥 финален bounce ефект
            el.classList.add("counter-pop");
            setTimeout(() => el.classList.remove("counter-pop"), 300);
        }
    }

    requestAnimationFrame(update);
}

/* =========================================================
   NAV ACTIVE STATE
   ========================================================= */

document.querySelectorAll('.nav-right a').forEach(link => {
    link.addEventListener('click', function () {
        document.querySelectorAll('.nav-right a')
            .forEach(l => l.classList.remove('active'));

        this.classList.add('active');
    });
});



function showToast(message, type = "error") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;

    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add("show"), 50);

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

function showError(message) {
    const modal = document.getElementById("errorModal");
    const text = document.getElementById("errorText");

    text.innerText = message;

    modal.classList.remove("hidden");

    setTimeout(() => {
        modal.classList.add("hidden");
    }, 3000);
}

