/* =========================================================
   GLOBAL STATE
   ========================================================= */

let selectedProvider = null;
let selectedProviderName = null;
let selectedServiceName = null;
let selectedServicePrice = null;
let selectedServiceDuration = null;
let selectedDateFormatted = null;
let selectedDay = null;


/* =========================================================
   TICKET — central render
   ========================================================= */

function updateTicket() {
    document.getElementById("ticketProvider").textContent = selectedProviderName || "—";
    document.getElementById("ticketProvider").classList.toggle("muted", !selectedProviderName);

    document.getElementById("ticketService").textContent = selectedServiceName || "—";
    document.getElementById("ticketService").classList.toggle("muted", !selectedServiceName);

    document.getElementById("ticketDate").textContent = selectedDateFormatted || "—";
    document.getElementById("ticketDate").classList.toggle("muted", !selectedDateFormatted);

    const time = document.getElementById("selectedTime").value;
    document.getElementById("ticketTime").textContent = time
        ? `${time}${selectedServiceDuration ? " · " + selectedServiceDuration + " мин" : ""}`
        : "—";
    document.getElementById("ticketTime").classList.toggle("muted", !time);

    document.getElementById("ticketPrice").textContent =
        selectedServicePrice !== null && selectedServicePrice !== undefined
            ? `${selectedServicePrice} лв.`
            : "—";
}


/* =========================================================
   PROVIDER SELECTION
   ========================================================= */

function selectProvider(e, id) {
    document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('active'));
    e.currentTarget.classList.add('active');

    selectedProvider = id;
    selectedProviderName = e.currentTarget.querySelector('.provider-name').textContent;

    // reset downstream selections
    selectedServiceName = null;
    selectedServicePrice = null;
    selectedServiceDuration = null;
    document.getElementById("service").value = "";
    document.getElementById("selectedTime").value = "";
    document.getElementById("slots").innerHTML = "";

    updateTicket();
    loadProviderServices(id);
    checkForm();
}


/* =========================================================
   SERVICES (динамично според избрания специалист)
   ========================================================= */

function loadProviderServices(providerId) {
    const container = document.getElementById("services");
    container.innerHTML = "<p>Зареждане...</p>";

    fetch(`/providers/${providerId}/services`)
        .then(r => r.json())
        .then(list => {
            container.innerHTML = "";

            if (!Array.isArray(list) || list.length === 0) {
                container.innerHTML = "<p>Този специалист все още няма добавени услуги</p>";
                return;
            }

            list.forEach(s => {
                const card = document.createElement("div");
                card.className = "service-card";
                card.innerHTML = `
                    <p>${s.service_name}</p>
                    <span class="service-meta">${s.duration_minutes} мин${s.price !== null ? " · " + s.price + " лв." : ""}</span>
                `;
                card.addEventListener("click", (e) => selectService(e, s));
                container.appendChild(card);
            });
        })
        .catch(() => {
            container.innerHTML = "<p>Грешка при зареждане на услугите</p>";
        });
}

function selectService(e, service) {
    document.querySelectorAll('.service-card').forEach(c => c.classList.remove('active'));
    e.currentTarget.classList.add('active');

    document.getElementById("service").value = service.service_id;
    selectedServiceName = service.service_name;
    selectedServicePrice = service.price;
    selectedServiceDuration = service.duration_minutes;

    // reset time since duration/availability may differ
    document.getElementById("selectedTime").value = "";
    document.getElementById("slots").innerHTML = "";

    updateTicket();

    document.getElementById('date').scrollIntoView({ behavior: 'smooth', block: 'center' });

    loadSlots();
    checkForm();
}


/* =========================================================
   SLOTS
   ========================================================= */

function loadSlots() {
    const date = document.getElementById("date").value;
    const service = document.getElementById("service").value;

    if (!selectedProvider || !date || !service) return;

    const container = document.getElementById("slots");
    container.innerHTML = "<p>Зареждане...</p>";

    fetch(`/availability?provider_id=${selectedProvider}&date=${date}&service_id=${service}`)
        .then(r => r.json())
        .then(slots => {
            container.innerHTML = "";

            if (!Array.isArray(slots) || slots.length === 0) {
                container.innerHTML = "<p>Няма свободни часове за тази дата</p>";
                return;
            }

            document.getElementById("selectedTime").value = "";
            updateTicket();

            slots.forEach(time => {
                const btn = document.createElement("button");
                btn.textContent = time;
                btn.classList.add("slot");
                btn.type = "button";
                btn.onclick = () => selectSlot(btn, time);
                container.appendChild(btn);
            });
        })
        .catch(() => {
            container.innerHTML = "<p>Грешка при зареждане</p>";
        });
}

function selectSlot(element, time) {
    document.querySelectorAll(".slot").forEach(s => s.classList.remove("active"));
    element.classList.add("active");

    document.getElementById("selectedTime").value = time;
    updateTicket();

    document.getElementById('name').scrollIntoView({ behavior: 'smooth', block: 'center' });
    checkForm();
}


/* =========================================================
   FORM VALIDATION
   ========================================================= */

function checkForm() {
    const name = document.getElementById("name").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const time = document.getElementById("selectedTime").value;
    const consent = document.getElementById("consent").checked;

    const btn = document.getElementById("submitBtn");
    btn.disabled = !(name && phone && time && selectedProvider && consent);
}

["name", "phone"].forEach(id => {
    document.getElementById(id).addEventListener("input", checkForm);
});
document.getElementById("consent").addEventListener("change", checkForm);


/* =========================================================
   BOOK
   ========================================================= */

function book() {
    const name = document.getElementById("name").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const email = document.getElementById("email").value.trim();
    const service = document.getElementById("service").value;
    const date = document.getElementById("date").value;
    const time = document.getElementById("selectedTime").value;
    const consent = document.getElementById("consent").checked;

    const btn = document.getElementById("submitBtn");
    const msg = document.getElementById("ticketMsg");
    msg.classList.add("hidden");

    if (!consent) {
        showToast("Трябва да се съгласите с обработката на лични данни.", "error");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Запазване...";

    fetch('/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name, phone, email, consent,
            provider_id: selectedProvider,
            service_id: service,
            appointment_time: `${date}T${time}:00`
        })
    })
        .then(async r => {
            let data;
            try { data = await r.json(); } catch { throw new Error("Сървърна грешка"); }
            if (!r.ok) throw new Error(data.error || "Грешка");
            return data;
        })
        .then(res => {
            confirmTicket(res.id);
            showToast("Часът е запазен успешно!");
        })
        .catch(err => {
            btn.disabled = false;
            btn.textContent = "Запази часа";
            msg.textContent = err.message;
            msg.classList.remove("hidden");
            showToast(err.message, "error");
        });
}

function confirmTicket(bookingId) {
    const ticket = document.getElementById("ticket");
    ticket.classList.add("confirmed");

    if (bookingId) {
        document.getElementById("ticketCode").textContent =
            "№ " + String(bookingId).padStart(6, "0");
    }
}

function resetBooking() {
    window.location.reload();
}


/* =========================================================
   NAVIGATION
   ========================================================= */

function goHome() {
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function goToBooking() {
    document.getElementById("providersSection").scrollIntoView({ behavior: "smooth", block: "start" });
}

window.addEventListener("scroll", () => {
    document.getElementById("nav").classList.toggle("scrolled", window.scrollY > 20);
});


/* =========================================================
   TOAST
   ========================================================= */

let toastTimer = null;

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast show ${type === "error" ? "error" : ""}`;

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
}


/* =========================================================
   DATE PICKER (Flatpickr)
   ========================================================= */

flatpickr("#date", {
    defaultDate: "today",
    dateFormat: "Y-m-d",
    minDate: "today",

    locale: {
        firstDayOfWeek: 1,
        weekdays: {
            shorthand: ["Нед", "Пон", "Вт", "Ср", "Чет", "Пет", "Съб"],
            longhand: ["Неделя", "Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота"]
        },
        months: {
            shorthand: ["Ян", "Фев", "Мар", "Апр", "Май", "Юни", "Юли", "Авг", "Сеп", "Окт", "Ное", "Дек"],
            longhand: ["Януари", "Февруари", "Март", "Април", "Май", "Юни", "Юли", "Август", "Септември", "Октомври", "Ноември", "Декември"]
        }
    },

    altInput: true,
    altFormat: "l, d F Y",
    disableMobile: true,

    onChange: function (selectedDates) {
        const d = selectedDates[0];
        if (!d) return;

        let day = d.toLocaleDateString("bg-BG", { weekday: "long" });
        selectedDay = day.charAt(0).toUpperCase() + day.slice(1);

        selectedDateFormatted = d.toLocaleDateString("bg-BG", {
            year: "numeric", month: "long", day: "numeric"
        });

        updateTicket();

        if (document.getElementById("service").value) {
            loadSlots();
        }
    }
});
