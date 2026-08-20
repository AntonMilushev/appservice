// =====================
// 🚀 INIT
// =====================
document.addEventListener("DOMContentLoaded", () => {
  init();

  const dateInput = document.getElementById("date");
  const manualDateInput = document.getElementById("manualDate");
  const serviceInput = document.getElementById("manualService");

  if (dateInput) {
    dateInput.addEventListener("change", () => {
      loadCalendar();
    });
  }

  if (manualDateInput) {
    manualDateInput.addEventListener("change", () => {
      onManualDateChange();
    });
  }

  if (serviceInput) {
    serviceInput.addEventListener("change", () => {
      loadManualSlots();
    });
  }

  ["manualName", "manualPhone", "manualService", "manualDate"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", updateManualSummary);
      el.addEventListener("change", updateManualSummary);
    }
  });
});

function init() {
  getDate();

  const manualDate = document.getElementById("manualDate");

  if (manualDate && !manualDate.value) {
    manualDate.value = new Date().toISOString().split("T")[0];
  }

  refreshAll();
  initPush();
  loadManualSlots();
  setInterval(refreshAll, 5000);

  initDayPicker("mySchWorkingDaysPicker");
  initToggle("mySchBreakToggle", "mySchBreakFields");
  initChipPicker("myAbsReasonPicker");
  initToggle("myAbsPartialToggle", "myAbsPartialFields");
}

function urlBase64ToUint8Array(base64String) {
  base64String = base64String.trim();

  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
}

const VAPID_PUBLIC_KEY = "BGE376lp-3TNjXN_1GTsT_b4YbsDFsSDayDuHnaeaVWKjAtGaPmk9Y9OYmUydelfDkoJ6GWSu8K8WoQ8MKuIs7c";

async function initPush() {
  if (!('serviceWorker' in navigator)) return;

  let reg = await navigator.serviceWorker.getRegistration();

  if (!reg) {
    reg = await navigator.serviceWorker.register('/sw.js');
  }

  reg = await navigator.serviceWorker.ready;

  if (!reg.active) {
    console.error("❌ SW not active yet");
    return;
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return;

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
  });

  console.log("SUB:", sub);

  await fetch('/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sub)
  });
}

// =====================
// 🔁 REFRESH ALL
// =====================
function refreshAll() {
  loadPending();
  loadCalendar();
  loadNotifications();
}

// =====================
// ⏳ PENDING
// =====================
function loadPending() {
  fetch('/provider/pending')
    .then(r => r.json())
    .then(data => {

      const container = document.getElementById("pendingList");
      if (!container) return;

      // Update badge
      const badge = document.getElementById("pendingBadge");
      if (badge) {
        if (data.length > 0) {
          badge.textContent = data.length;
          badge.style.display = "inline-block";
        } else {
          badge.style.display = "none";
        }
      }

      if (data.length === 0) {
        container.innerHTML = `<p style="color:var(--text-muted);font-size:12px;letter-spacing:0.06em;">Няма чакащи заявки</p>`;
        return;
      }

      container.innerHTML = data.map(b => {
        const dateObj = new Date(b.datetime);

        const date = dateObj.toLocaleDateString("bg-BG", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric"
        });

        const time = dateObj.toTimeString().slice(0, 5);

        return `
    <div class="pending-card">
        <strong>${b.name}</strong>
        ✂️ ${b.service}<br>
        📞 ${b.phone}<br>
        📅 ${date}<br>
        ⏰ ${time}

        <div class="actions">
            <button class="approve" onclick="approve(${b.id})">✔</button>
            <button class="reject" onclick="reject(${b.id})">✖</button>
        </div>
    </div>
  `;
      }).join('');
    });
}

// =====================
// 📅 CALENDAR
// =====================
function timeToMinutes(str) {
  const [h, m] = str.split(':').map(Number);
  return h * 60 + m;
}

function minutesToTime(mins) {
  const h = String(Math.floor(mins / 60)).padStart(2, '0');
  const m = String(mins % 60).padStart(2, '0');
  return `${h}:${m}`;
}

function buildHourRange(workStart, workEnd, bookings) {
  let startMin = timeToMinutes(workStart);
  let endMin = timeToMinutes(workEnd);

  // 🛡 защита: ако има booking извън текущия работен диапазон
  // (напр. стар час, направен при друг график), мрежата се разширява,
  // за да не "изчезва" визуално от календара
  bookings.forEach(b => {
    const t = new Date(b.start);
    const startOfBooking = t.getHours() * 60 + t.getMinutes();

    const tEnd = new Date(b.end);
    const endOfBooking = tEnd.getHours() * 60 + tEnd.getMinutes();

    if (startOfBooking < startMin) startMin = startOfBooking;
    if (endOfBooking > endMin) endMin = endOfBooking;
  });

  startMin = Math.floor(startMin / 30) * 30;
  endMin = Math.ceil(endMin / 30) * 30;

  const hours = [];
  for (let m = startMin; m < endMin; m += 30) {
    hours.push(minutesToTime(m));
  }
  return hours;
}

function loadCalendar() {
  const date = getDate();

  fetch(`/provider/schedule?date=${date}`)
    .then(r => r.json())
    .then(data => {
      const container = document.getElementById("calendar");
      if (!container) return;

      const bookings = data.bookings || [];
      const hours = buildHourRange(
        data.working_start || "09:00",
        data.working_end || "19:00",
        bookings
      );

      container.innerHTML = hours.map(hour => {
        const booking = bookings.find(b => {
          const t = new Date(b.start);
          return t.toTimeString().slice(0, 5) === hour;
        });

        if (booking) {
          return `
    <div class="calendar-slot">
        <strong>${hour}</strong>

        <div class="booking booking--confirmed" onclick="openSheet(${booking.id})">
             <strong>${booking.name}</strong>
             ${booking.service}<br>
          📞 ${booking.phone}
        </div>

        <div class="actions">
            <button class="delete" onclick="deleteBooking(${booking.id})">🗑</button>
        </div>
    </div>
  `;
        }

        return `
          <div class="calendar-slot">
            <strong>${hour}</strong>
          </div>
        `;
      }).join('');
    });
}

// =====================
// ✔ ACTIONS
// =====================
function approve(id) {
  fetch(`/booking/${id}/approve`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      console.log("APPROVE:", data);
      refreshAll();
    })
    .catch(err => console.error("ERROR:", err));
}

function reject(id) {
  fetch(`/booking/${id}/reject`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      console.log("REJECT:", data);
      refreshAll();
    })
    .catch(err => console.error(err));
}

// =====================
// 📅 DATE
// =====================
function getDate() {
  const input = document.getElementById("date");

  if (!input.value) {
    input.value = new Date().toISOString().split("T")[0];
  }

  return input.value;
}

function changeDay(offset) {
  const input = document.getElementById("date");

  let d = new Date(input.value);
  d.setDate(d.getDate() + offset);

  input.value = d.toISOString().split("T")[0];

  loadCalendar();
  loadManualSlots();
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

// =====================
// 🔔 NOTIFICATIONS
// =====================
function loadNotifications() {
  fetch('/provider/notifications')
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById("notifText");
      if (!el) return;

      if (d.pending_count === 0) {
        el.innerText = "Няма заявки";
      } else if (d.pending_count === 1) {
        el.innerText = "1 чакаща заявка";
      } else {
        el.innerText = `${d.pending_count} чакащи заявки`;
      }

      updateNotifStyle(d.pending_count);
    });
}

function updateNotifStyle(count) {
  const el = document.querySelector(".notif");
  if (!el) return;

  if (count > 0) {
    el.classList.add("active");
  } else {
    el.classList.remove("active");
  }
}

function scrollToPending() {
  const el = document.querySelector(".pending-section");
  if (!el) return;

  el.scrollIntoView({ behavior: "smooth" });
}

function deleteBooking(id) {
  if (!confirm("Сигурен ли си?")) return;

  fetch(`/booking/${id}/delete`, { method: 'POST' })
    .then(refreshAll);
}

// =====================
// 📋 ACTION SHEET
// =====================
let selectedBookingId = null;

function openSheet(id) {
  selectedBookingId = id;

  document.getElementById("actionSheet").classList.remove("hidden");
  const overlay = document.getElementById("sheetOverlay");
  if (overlay) overlay.classList.remove("hidden");
}

function closeSheet() {
  document.getElementById("actionSheet").classList.add("hidden");
  const overlay = document.getElementById("sheetOverlay");
  if (overlay) overlay.classList.add("hidden");
}

document.getElementById("approveBtn").onclick = () => {
  approve(selectedBookingId);
  closeSheet();
};

document.getElementById("rejectBtn").onclick = () => {
  reject(selectedBookingId);
  closeSheet();
};

document.getElementById("deleteBtn").onclick = () => {
  deleteBooking(selectedBookingId);
  closeSheet();
};

document.onmousemove = resetTimer;
document.onkeypress = resetTimer;


function addManualBooking() {
  const name = document.getElementById("manualName").value.trim();
  const phone = document.getElementById("manualPhone").value.trim();
  const service = document.getElementById("manualService").value;
  const date = document.getElementById("manualDate").value;
  const time = document.getElementById("manualSelectedTime").value;

  if (!name || !phone || !service || !date || !time) {
    alert("Попълни всички полета и избери свободен час");
    return;
  }

  fetch("/provider/add-booking", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: name,
      phone: phone,
      service_id: service,
      appointment_time: `${date}T${time}:00`
    })
  })
    .then(async response => {
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Грешка при добавяне");
      }

      return data;
    })
    .then(() => {
      alert("Часът е добавен успешно.");

      document.getElementById("manualName").value = "";
      document.getElementById("manualPhone").value = "";
      document.getElementById("manualSelectedTime").value = "";

      refreshAll();
      loadManualSlots();
    })
    .catch(error => {
      alert(error.message);
    });
}


function loadManualSlots() {
  const date = document.getElementById("manualDate").value;
  const service = document.getElementById("manualService").value;
  const container = document.getElementById("manualSlots");
  const selectedTime = document.getElementById("manualSelectedTime");

  if (!container || !selectedTime) return;

  selectedTime.value = "";
  container.innerHTML = "";

  updateManualSummary();

  if (!date || !service) {
    container.innerHTML = "<p>Избери дата и услуга</p>";
    return;
  }

  fetch(`/provider/available-slots?date=${date}&service_id=${service}`)
    .then(async response => {
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Грешка при зареждане");
      }

      return data;
    })
    .then(slots => {
      container.innerHTML = "";

      if (!Array.isArray(slots) || slots.length === 0) {
        container.innerHTML = "<p>Няма свободни часове за избраната дата</p>";
        return;
      }

      slots.forEach(time => {
        const btn = document.createElement("button");

        btn.type = "button";
        btn.textContent = time;
        btn.className = "manual-slot";

        btn.addEventListener("click", () => {
          document.querySelectorAll(".manual-slot").forEach(slot => {
            slot.classList.remove("active");
          });

          btn.classList.add("active");
          selectedTime.value = time;

          updateManualSummary();
        });

        container.appendChild(btn);
      });
    })
    .catch(error => {
      container.innerHTML = `<p>${error.message}</p>`;
    });
}


function onProviderDateChange() {
  loadCalendar();
  loadManualSlots();
}

function onManualDateChange() {
  const manualDate = document.getElementById("manualDate").value;
  const calendarDate = document.getElementById("date");

  calendarDate.value = manualDate;

  loadCalendar();
  loadManualSlots();
}

function updateManualSummary() {
  const name = document.getElementById("manualName").value.trim();
  const phone = document.getElementById("manualPhone").value.trim();
  const serviceSelect = document.getElementById("manualService");
  const date = document.getElementById("manualDate").value;
  const time = document.getElementById("manualSelectedTime").value;

  const summary = document.getElementById("manualSummary");

  if (!name && !phone && !serviceSelect.value && !date && !time) {
    summary.classList.add("hidden");
    return;
  }

  summary.classList.remove("hidden");

  document.getElementById("manualSumName").innerText = name || "-";
  document.getElementById("manualSumPhone").innerText = phone || "-";
  document.getElementById("manualSumService").innerText =
    serviceSelect.options[serviceSelect.selectedIndex]?.text || "-";
  document.getElementById("manualSumTime").innerText = time || "-";

  if (date) {
    const d = new Date(date);

    document.getElementById("manualSumDate").innerText =
      d.toLocaleDateString("bg-BG", {
        day: "2-digit",
        month: "long",
        year: "numeric"
      });

    document.getElementById("manualSumDay").innerText =
      d.toLocaleDateString("bg-BG", { weekday: "long" });
  } else {
    document.getElementById("manualSumDate").innerText = "-";
    document.getElementById("manualSumDay").innerText = "-";
  }
}


function openMySchedule() {
  document.getElementById("scheduleSheet").classList.remove("hidden");
  document.getElementById("scheduleOverlay").classList.remove("hidden");

  fetch('/provider/settings')
    .then(r => r.json())
    .then(data => {
      setSelectedDays("mySchWorkingDaysPicker", data.working_days || "");
      document.getElementById("mySchStart").value = data.working_start || "";
      document.getElementById("mySchEnd").value = data.working_end || "";

      const hasBreak = !!(data.break_start || data.break_end);
      document.getElementById("mySchBreakToggle").checked = hasBreak;
      document.getElementById("mySchBreakFields").classList.toggle("hidden", !hasBreak);
      document.getElementById("mySchBreakStart").value = data.break_start || "";
      document.getElementById("mySchBreakEnd").value = data.break_end || "";
    });

  loadMyAbsences();
}

function closeMySchedule() {
  document.getElementById("scheduleSheet").classList.add("hidden");
  document.getElementById("scheduleOverlay").classList.add("hidden");
}

function saveMySchedule() {
  const hasBreak = document.getElementById("mySchBreakToggle").checked;

  fetch('/provider/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      working_days: getSelectedDays("mySchWorkingDaysPicker"),
      working_start: document.getElementById("mySchStart").value,
      working_end: document.getElementById("mySchEnd").value,
      break_start: hasBreak ? document.getElementById("mySchBreakStart").value : "",
      break_end: hasBreak ? document.getElementById("mySchBreakEnd").value : ""
    })
  })
    .then(r => r.json())
    .then(res => {
      if (res.error) { alert(res.error); return; }
      alert("Графикът е запазен");
      loadCalendar();
      loadManualSlots();
    })
    .catch(() => alert("Грешка при запис"));
}

function loadMyAbsences() {
  fetch('/provider/absences')
    .then(r => r.json())
    .then(list => {
      const container = document.getElementById("myAbsenceList");

      if (!Array.isArray(list) || list.length === 0) {
        container.innerHTML = "<p style='color:var(--text-muted);font-size:12px;'>Няма планирани отсъствия</p>";
        return;
      }

      container.innerHTML = list.map(a => `
        <div class="pending-card" style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <strong>${a.reason}</strong><br>
            <span style="font-size:11px;color:var(--text-sub);">
              ${a.start_date}${a.end_date !== a.start_date ? ' → ' + a.end_date : ''}
              ${a.unavailable_from ? ' (' + a.unavailable_from + (a.unavailable_to ? '–' + a.unavailable_to : ' до края на деня') + ')' : ''}
            </span>
          </div>
          <button class="delete" onclick="removeMyAbsence(${a.id})">🗑</button>
        </div>
      `).join('');
    });
}

function addMyAbsence() {
  const start = document.getElementById("myAbsStart").value;
  const end = document.getElementById("myAbsEnd").value || start;
  const isPartial = document.getElementById("myAbsPartialToggle").checked;

  if (!start) {
    alert("Избери начална дата");
    return;
  }

  fetch('/provider/absences', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_date: start,
      end_date: end,
      reason: getActiveChip("myAbsReasonPicker") || "Отпуск",
      unavailable_from: isPartial ? (document.getElementById("myAbsFrom").value || null) : null,
      unavailable_to: isPartial ? (document.getElementById("myAbsTo").value || null) : null
    })
  })
    .then(async r => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Грешка");
      return data;
    })
    .then(data => {
      if (data.conflicts && data.conflicts.length > 0) {
        alert(`⚠️ Внимание: ${data.conflicts.length} съществуващ(и) час(а) попадат в този период.`);
      }

      document.getElementById("myAbsStart").value = "";
      document.getElementById("myAbsEnd").value = "";
      document.getElementById("myAbsFrom").value = "";
      document.getElementById("myAbsTo").value = "";
      document.getElementById("myAbsPartialToggle").checked = false;
      document.getElementById("myAbsPartialFields").classList.add("hidden");

      loadMyAbsences();
      loadCalendar();
    })
    .catch(err => alert(err.message));
}

function removeMyAbsence(id) {
  if (!confirm("Сигурен ли си?")) return;

  fetch(`/provider/absences/${id}`, { method: 'DELETE' })
    .then(loadMyAbsences);
}

// =====================
// 🧩 SIMPLIFIED SCHEDULE HELPERS
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

function initDayPicker(pickerId) {
  const picker = document.getElementById(pickerId);
  if (!picker) return;
  picker.querySelectorAll(".day-btn").forEach(btn => {
    btn.addEventListener("click", () => btn.classList.toggle("active"));
  });
}

function initChipPicker(pickerId) {
  const picker = document.getElementById(pickerId);
  if (!picker) return;
  picker.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      picker.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
    });
  });
}

function getActiveChip(pickerId) {
  const el = document.querySelector(`#${pickerId} .chip.active`);
  return el ? el.dataset.reason : "";
}

function initToggle(checkboxId, sectionId) {
  const checkbox = document.getElementById(checkboxId);
  const section = document.getElementById(sectionId);
  if (!checkbox || !section) return;
  checkbox.addEventListener("change", () => {
    section.classList.toggle("hidden", !checkbox.checked);
    if (!checkbox.checked) {
      section.querySelectorAll("input").forEach(i => i.value = "");
    }
  });
}