// =====================
// 🌍 GLOBAL
// =====================
let uploadedImage = null;
const DEFAULT_IMG = "/static/images/default.png";


function timeToMinutes(str) {
    const [h, m] = str.split(':').map(Number);
    return h * 60 + m;
}

function minutesToTime(mins) {
    const h = String(Math.floor(mins / 60)).padStart(2, '0');
    const m = String(mins % 60).padStart(2, '0');
    return `${h}:${m}`;
}

function buildHourRange(workStart, workEnd, bookingTimes) {
    let startMin = timeToMinutes(workStart);
    let endMin = timeToMinutes(workEnd);

    // 🛡 защита: ако има booking извън текущия работен диапазон
    // (напр. стар час, направен при друг график), мрежата се разширява
    bookingTimes.forEach(hhmm => {
        const mins = timeToMinutes(hhmm);
        if (mins < startMin) startMin = mins;
        if (mins + 30 > endMin) endMin = mins + 30;
    });

    startMin = Math.floor(startMin / 30) * 30;
    endMin = Math.ceil(endMin / 30) * 30;

    const hours = [];
    for (let m = startMin; m < endMin; m += 30) {
        hours.push(minutesToTime(m));
    }
    return hours;
}

function load() {
    console.log("LOAD RUNNING");

    const date = getSelectedDate();

    fetch(`/admin/dashboard?date=${date}`)
        .then(r => {
            if (r.status === 403) {
                window.location = "/login";
                return null;
            }
            return r.json();
        })
        .then(data => {
            if (!data || !Array.isArray(data)) return;

            const container = document.getElementById("admin");
            if (!container) return;

            const now = new Date();
            const selectedDate = new Date(date);

            container.innerHTML = `
                <div class="schedule-grid">
                    ${data.map(barber => {

                const workStart = barber.working_start || "09:00";
                const workEnd = barber.working_end || "19:00";

                // ✅ времена на съществуващите резервации за този барбър
                const bookingTimes = barber.bookings
                    .filter(b => b.time && b.time.split(" ")[0] === date)
                    .map(b => b.time.split(" ")[1].substring(0, 5));

                // ✅ мрежата вече е динамична спрямо реалния график
                const hours = buildHourRange(workStart, workEnd, bookingTimes);

                return `
                        <div class="barber-column">
                            <h3>${barber.barber}</h3>

                            ${hours.map(hour => {

                    const [h, m] = hour.split(":");
                    const slotTime = new Date(selectedDate);
                    slotTime.setHours(h, m, 0, 0);

                    const isPast = slotTime < now;

                    // ✅ филтър по дата + час
                    const bookingsForSlot = barber.bookings.filter(b => {
                        if (!b.time) return false;

                        const datePart = b.time.split(" ")[0];
                        if (datePart !== date) return false;

                        const time = b.time.split(" ")[1].substring(0, 5);
                        return time === hour;
                    });

                    // ✅ ако има booking-и
                    if (bookingsForSlot.length > 0) {
                        return `
                                <div class="time-slot booked">
                                    <strong>${hour}</strong><br>

                                    ${bookingsForSlot.map(booking => {

                            let statusClass = "";
                            if (booking.status === "PENDING") statusClass = "booking--pending";
                            if (booking.status === "CONFIRMED") statusClass = "booking--confirmed";
                            if (booking.status === "CANCELLED") statusClass = "booking--cancelled";

                            return `
                                    <div class="booking ${statusClass}">
                                        <strong>${booking.name}</strong><br>
                                        ${booking.service}

                                        <div class="actions">
                                            ${booking.status === "PENDING" ? `
                                                <button class="approve" onclick="approve(${booking.id})">✔</button>
                                                <button class="reject" onclick="reject(${booking.id})">✖</button>
                                            ` : ""}
                                            <button class="delete" onclick="deleteBooking(${booking.id})">🗑</button>
                                        </div>
                                    </div>
                                `;
                        }).join("")}

                                </div>
                            `;
                    }

                    // ❌ празен слот
                    return `<div class="time-slot ${isPast ? 'time-slot--past' : ''}">
                                    <strong>${hour}</strong>
                                </div>`;

                }).join('')}

                        </div>
                    `;
            }).join('')}
                </div>
            `;
        })
        .catch(err => console.error("Dashboard error:", err));
}
document.getElementById("adminDate").addEventListener("change", load);

function approve(id) {
    fetch(`/admin/approve/${id}`, { method: 'POST' })
        .then(load);
}

function reject(id) {
    fetch(`/admin/reject/${id}`, { method: 'POST' })
        .then(load);
}

function deleteBooking(id) {
    fetch(`/admin/delete/${id}`, { method: 'POST' })
        .then(load);
}


// =====================
// 👨‍🦱 BARBERS CRUD
// =====================
function loadBarbers() {
    fetch('/admin/barbers')
        .then(r => r.json())
        .then(data => {
            if (!Array.isArray(data)) return;

            const container = document.getElementById("barbers");
            if (!container) return;

            container.innerHTML = data.map(b => `
                <div class="card">
                    <img 
                        src="${b.image || DEFAULT_IMG}" 
                        width="80"
                        onerror="this.src='${DEFAULT_IMG}'"
                    >
                    <h3>${b.name}</h3>

                    <div class="card-menu">
                        <button class="card-menu__trigger" onclick="toggleCardMenu(event, ${b.id})">⋮</button>
                        <div class="card-menu__dropdown hidden" id="cardMenu-${b.id}">
                            <button onclick="editBarber(${b.id})">✏️ Редактирай</button>
                            <button onclick="openSchedule(${b.id}, '${(b.name || '').replace(/'/g, "\\'")}')">⚙️ График</button>
                            <button class="danger" onclick="deleteBarber(${b.id})">🗑️ Изтрий</button>
                        </div>
                    </div>
                </div>
            `).join('');
        })
        .catch(() => console.error("Barbers load error"));
}

// =====================
// 📋 CARD ACTIONS MENU
// =====================
function toggleCardMenu(event, id) {
    event.stopPropagation();
    const menu = document.getElementById(`cardMenu-${id}`);
    if (!menu) return;

    const isOpen = !menu.classList.contains("hidden");

    document.querySelectorAll(".card-menu__dropdown").forEach(m => m.classList.add("hidden"));

    if (!isOpen) menu.classList.remove("hidden");
}

document.addEventListener("click", () => {
    document.querySelectorAll(".card-menu__dropdown").forEach(m => m.classList.add("hidden"));
});

// ➕ CREATE
function createBarber() {
    const nameInput = document.getElementById("name");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    if (!nameInput || !usernameInput || !passwordInput) return;

    const name = nameInput.value.trim();
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    // 🔴 validation
    if (!name || !username || !password) {
        alert("Попълни всички полета!");
        return;
    }

    if (password.length < 4) {
        alert("Паролата трябва да е поне 4 символа");
        return;
    }

    fetch('/admin/barber', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name,
            username,
            password,
            image: uploadedImage
        })
    })
        .then(res => res.json())
        .then(res => {
            if (res.error) {
                alert(res.error);
                return;
            }

            alert("Барбър създаден успешно!");

            // 🔥 reset form
            nameInput.value = "";
            usernameInput.value = "";
            passwordInput.value = "";
            uploadedImage = null;

            const preview = document.getElementById("preview");
            if (preview) {
                preview.style.display = "none";
                preview.src = "";
            }

            loadBarbers();
        })
        .catch(() => alert("Грешка при добавяне"));
}

// ✏️ UPDATE
function editBarber(id) {
    const name = prompt("Ново име:");
    if (!name) return;

    fetch(`/admin/barber/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    })
        .then(loadBarbers)
        .catch(() => alert("Грешка при редакция"));
}


// ❌ DELETE
function deleteBarber(id) {
    if (!confirm("Сигурен ли си?")) return;

    fetch(`/admin/barber/${id}`, {
        method: 'DELETE'
    })
        .then(loadBarbers)
        .catch(() => alert("Грешка при изтриване"));
}


// =====================
// 📸 IMAGE UPLOAD
// =====================
function initUpload() {
    const input = document.getElementById("imageFile");
    if (!input) return;

    input.addEventListener("change", function () {
        const file = this.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (e) {
            const preview = document.getElementById("preview");
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = "block";
            }
        };
        reader.readAsDataURL(file);

        const formData = new FormData();
        formData.append("image", file);

        fetch('/admin/upload', {
            method: 'POST',
            body: formData
        })
            .then(r => r.json())
            .then(res => {
                if (res.error) {
                    alert(res.error);
                    return;
                }

                uploadedImage = res.url;
            })
            .catch(() => alert("Upload грешка"));
    });
}


// =====================
// 📜 LOGS
// =====================
function loadLogs() {
    fetch('/admin/logs')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById("logs");
            if (!container) return;

            container.innerHTML = data.map(l => `
                <div class="card">
                    <strong>${l.action}</strong><br>
                    ${l.desc}<br>
                    🕒 ${l.time}
                </div>
            `).join('');
        })
        .catch(() => console.error("Logs error"));
}


// =====================
// 🚪 LOGOUT
// =====================
function logout() {
    fetch('/logout')
        .then(() => window.location = "/login");
}


// =====================
// ⏱ AUTO LOGOUT
// =====================
let timer;

function resetTimer() {
    clearTimeout(timer);
    timer = setTimeout(() => {
        alert("Сесията изтече");
        logout();
    }, 30 * 60 * 1000);
}

function getSelectedDate() {
    const input = document.getElementById("adminDate");

    if (!input.value) {
        const today = new Date();
        const formatted = today.toISOString().split("T")[0];
        input.value = formatted;
    }

    return input.value;
}


function changeDay(offset) {
    const input = document.getElementById("adminDate");

    let current = input.value
        ? new Date(input.value)
        : new Date();

    current.setDate(current.getDate() + offset);

    const newDate = current.toISOString().split("T")[0];
    input.value = newDate;

    load(); // 🔥 презарежда календара
}

function updateDayLabel() {
    const input = document.getElementById("adminDate");
    const label = document.getElementById("dayLabel");

    if (!input.value) return;

    const date = new Date(input.value);

    const days = ["Нед", "Пон", "Вто", "Сря", "Чет", "Пет", "Съб"];

    label.textContent = days[date.getDay()];
}

function goToday() {
    const today = new Date().toISOString().split("T")[0];
    document.getElementById("adminDate").value = today;

    updateDayLabel();
    load();
}


setInterval(() => {
    console.log("AUTO REFRESH");
    load();
}, 10000);


// =====================
// 🧩 SIMPLIFIED SCHEDULE HELPERS (event delegation — работи винаги)
// =====================
function getSelectedDays(pickerId) {
    return Array.from(document.querySelectorAll(`#${pickerId} .day-btn.active`))
        .map(b => b.dataset.day)
        .join(",");
}

function setSelectedDays(pickerId, daysStr) {
    const days = (daysStr || "").split(",").map(d => d.trim()).filter(Boolean);
    document.querySelectorAll(`#${pickerId} .day-btn`).forEach(btn => {
        btn.classList.toggle("active", days.includes(btn.dataset.day));
    });
}

function getActiveChip(pickerId) {
    const el = document.querySelector(`#${pickerId} .chip.active`);
    return el ? el.dataset.reason : "";
}

document.addEventListener("click", (e) => {
    const dayBtn = e.target.closest(".day-btn");
    if (dayBtn) {
        dayBtn.classList.toggle("active");
        return;
    }

    const chip = e.target.closest(".chip");
    if (chip) {
        const picker = chip.closest(".chip-picker");
        if (picker) {
            picker.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
        }
        chip.classList.add("active");
        return;
    }
});

document.addEventListener("change", (e) => {
    if (e.target.id === "schBreakToggle") {
        document.getElementById("schBreakFields").classList.toggle("hidden", !e.target.checked);
    }
    if (e.target.id === "absPartialToggle") {
        document.getElementById("absPartialFields").classList.toggle("hidden", !e.target.checked);
    }
});


// =====================
// 🚀 INIT
// =====================
window.onload = function () {
    resetTimer();
    initUpload();
    load();
    loadBarbers();
    loadSmsLogs(1);
};


let currentScheduleBarberId = null;

function openSchedule(id, name) {
    currentScheduleBarberId = id;
    document.getElementById("scheduleBarberName").innerText = name;
    document.getElementById("scheduleModal").classList.remove("hidden");

    fetch(`/admin/barber/${id}/settings`)
        .then(r => r.json())
        .then(data => {
            setSelectedDays("schWorkingDaysPicker", data.working_days || "");
            document.getElementById("schStart").value = data.working_start || "";
            document.getElementById("schEnd").value = data.working_end || "";

            const hasBreak = !!(data.break_start || data.break_end);
            document.getElementById("schBreakToggle").checked = hasBreak;
            document.getElementById("schBreakFields").classList.toggle("hidden", !hasBreak);
            document.getElementById("schBreakStart").value = data.break_start || "";
            document.getElementById("schBreakEnd").value = data.break_end || "";
        });

    loadBarberAbsences();
}

function closeScheduleModal() {
    document.getElementById("scheduleModal").classList.add("hidden");
    currentScheduleBarberId = null;
}

function saveBarberSchedule() {
    if (!currentScheduleBarberId) return;

    const hasBreak = document.getElementById("schBreakToggle").checked;

    fetch(`/admin/barber/${currentScheduleBarberId}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            working_days: getSelectedDays("schWorkingDaysPicker"),
            working_start: document.getElementById("schStart").value,
            working_end: document.getElementById("schEnd").value,
            break_start: hasBreak ? document.getElementById("schBreakStart").value : "",
            break_end: hasBreak ? document.getElementById("schBreakEnd").value : ""
        })
    })
        .then(r => r.json())
        .then(res => {
            if (res.error) { alert(res.error); return; }
            alert("Графикът е запазен");
        })
        .catch(() => alert("Грешка при запис"));
}

function loadBarberAbsences() {
    if (!currentScheduleBarberId) return;

    fetch(`/admin/barber/${currentScheduleBarberId}/absences`)
        .then(r => r.json())
        .then(list => {
            const container = document.getElementById("absenceList");

            if (!Array.isArray(list) || list.length === 0) {
                container.innerHTML = "<p style='color:var(--text-sub);font-size:12px;'>Няма отсъствия</p>";
                return;
            }

            container.innerHTML = list.map(a => `
        <div class="card" style="width:100%; text-align:left; display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div>
            <strong>${a.reason}</strong><br>
            <span style="font-size:12px;color:var(--text-sub);">
              ${a.start_date}${a.end_date !== a.start_date ? ' → ' + a.end_date : ''}
              ${a.unavailable_from ? ' (' + a.unavailable_from + (a.unavailable_to ? '–' + a.unavailable_to : ' до края на деня') + ')' : ''}
            </span>
          </div>
          <button class="delete" onclick="removeAbsence(${a.id})">🗑</button>
        </div>
      `).join('');
        });
}

function addBarberAbsence() {
    if (!currentScheduleBarberId) return;

    const start = document.getElementById("absStart").value;
    const end = document.getElementById("absEnd").value || start;
    const isPartial = document.getElementById("absPartialToggle").checked;

    if (!start) {
        alert("Избери начална дата");
        return;
    }

    fetch(`/admin/barber/${currentScheduleBarberId}/absences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start_date: start,
            end_date: end,
            reason: getActiveChip("absReasonPicker") || "Отпуск",
            unavailable_from: isPartial ? (document.getElementById("absFrom").value || null) : null,
            unavailable_to: isPartial ? (document.getElementById("absTo").value || null) : null
        })
    })
        .then(async r => {
            const data = await r.json();
            if (!r.ok) throw new Error(data.error || "Грешка");
            return data;
        })
        .then(data => {
            if (data.conflicts && data.conflicts.length > 0) {
                alert(`⚠️ Внимание: ${data.conflicts.length} съществуващ(и) час(а) попадат в този период. Свържи се с клиентите при нужда.`);
            }

            document.getElementById("absStart").value = "";
            document.getElementById("absEnd").value = "";
            document.getElementById("absFrom").value = "";
            document.getElementById("absTo").value = "";
            document.getElementById("absPartialToggle").checked = false;
            document.getElementById("absPartialFields").classList.add("hidden");

            loadBarberAbsences();
        })
        .catch(err => alert(err.message));
}

function removeAbsence(id) {
    if (!confirm("Сигурен ли си?")) return;

    fetch(`/admin/absences/${id}`, { method: 'DELETE' })
        .then(loadBarberAbsences);
}

let smsCurrentPage = 1;
let smsLastQuery = { phone: "", success: "" };

function loadSmsLogs(page = smsCurrentPage) {
    const phone = document.getElementById("smsPhoneFilter").value.trim();
    const success = document.getElementById("smsSuccessFilter").value;

    smsCurrentPage = page;
    smsLastQuery = { phone, success };

    const params = new URLSearchParams();
    if (phone) params.set("phone", phone);
    if (success) params.set("success", success);
    params.set("page", page);

    fetch(`/admin/sms-logs?${params}`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById("smsLogs");

            if (!data.items || data.items.length === 0) {
                container.innerHTML = "<p style='color:var(--text-sub);font-size:12px;'>Няма записи</p>";
                document.getElementById("smsPagination").innerHTML = "";
                return;
            }

            container.innerHTML = data.items.map(l => `
                <div class="card" style="width:100%; text-align:left; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong style="color:${l.success ? 'var(--success)' : '#e06b62'}">
                            ${l.success ? '✔' : '✖'} ${l.phone}
                        </strong> — ${l.status_type}<br>
                        <span style="font-size:12px;color:var(--text-sub);">${l.message}</span><br>
                        ${l.error ? `<span style="font-size:11px;color:#e06b62;">${l.error}</span><br>` : ""}
                        <span style="font-size:11px;color:var(--text-muted);">${l.created_at}</span>
                    </div>
                    <button class="delete" onclick="deleteSmsLog(${l.id})">🗑</button>
                </div>
            `).join('');

            renderSmsPagination(data.page, data.total_pages, data.total);
        });
}

function renderSmsPagination(page, totalPages, total) {
    const el = document.getElementById("smsPagination");

    if (totalPages <= 1) {
        el.innerHTML = `<span style="font-size:11px;color:var(--text-sub);">${total} записа</span>`;
        return;
    }

    el.innerHTML = `
        <button class="btn btn--nav" ${page <= 1 ? "disabled" : ""} onclick="loadSmsLogs(${page - 1})">&#8592;</button>
        <span style="font-size:12px;color:var(--text-sub);">Стр. ${page} / ${totalPages} (${total} общо)</span>
        <button class="btn btn--nav" ${page >= totalPages ? "disabled" : ""} onclick="loadSmsLogs(${page + 1})">&#8594;</button>
    `;
}

function deleteSmsLog(id) {
    if (!confirm("Изтриване на този SMS лог?")) return;

    fetch(`/admin/sms-logs/${id}`, { method: 'DELETE' })
        .then(() => loadSmsLogs(smsCurrentPage));
}

function deleteAllSmsLogs() {
    const { phone, success } = smsLastQuery;

    const msg = (phone || success)
        ? "Изтриване на ВСИЧКИ логове, отговарящи на текущия филтър?"
        : "Изтриване на ВСИЧКИ SMS логове? Това не може да бъде отменено.";

    if (!confirm(msg)) return;

    const params = new URLSearchParams();
    if (phone) params.set("phone", phone);
    if (success) params.set("success", success);

    fetch(`/admin/sms-logs?${params}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(res => {
            alert(`Изтрити ${res.count} записа`);
            loadSmsLogs(1);
        });
}

document.onmousemove = resetTimer;
document.onkeypress = resetTimer;