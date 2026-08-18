function load() {
    fetch('/admin/monitoring/stats')
        .then(r => {
            if (r.status === 403) {
                window.location = "/login";
                return null;
            }
            return r.json();
        })
        .then(data => {
            if (!data) return;

            console.log("MONITORING DATA:", data);
            console.log("ACTIVITY:", data.activity);

            renderBookings(data.bookings);
            renderSms(data.sms);
            renderEmail(data.email);
            renderActivity(data.activity);
        })
        .catch(err => console.error("Monitoring load error:", err));
}

function statCard(label, value, color) {
    return `
        <div class="card">
            <h3 style="color:${color || 'var(--gold)'}; font-size:28px; font-family: var(--font-display);">${value}</h3>
            <p style="font-size:12px; color:var(--text-sub); margin-top:6px;">${label}</p>
        </div>
    `;
}

function renderBookings(b) {
    document.getElementById("bookingStats").innerHTML = `
        ${statCard("Чакащи", b.pending, "var(--warning)")}
        ${statCard("Потвърдени днес", b.today_confirmed, "var(--success)")}
        ${statCard("Отказани днес", b.today_cancelled, "#e06b62")}
        ${statCard("Общо днес", b.today_total)}
    `;
}

function renderSms(s) {
    document.getElementById("smsStats").innerHTML = `
        <div class="barbers-grid">
            ${statCard("Успешни", s.success_24h, "var(--success)")}
            ${statCard("Неуспешни", s.failed_24h, "#e06b62")}
        </div>
    `;

    const container = document.getElementById("smsFailures");

    if (!s.recent_failures || s.recent_failures.length === 0) {
        container.innerHTML = "<p style='color:var(--text-sub);font-size:12px;'>Няма скорошни грешки</p>";
        return;
    }

    container.innerHTML = "<h3 style='margin-bottom:10px;'>Последни грешки</h3>" + s.recent_failures.map(f => `
        <div class="card" style="width:100%; text-align:left; display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div>
                <strong style="color:#e06b62;">${f.phone}</strong> — ${f.status_type || "-"}<br>
                <span style="font-size:11px;color:var(--text-sub);">${f.error || ""}</span>
            </div>
            <span style="font-size:11px;color:var(--text-muted);">${f.created_at}</span>
        </div>
    `).join('');
}

function renderEmail(e) {
    document.getElementById("emailStats").innerHTML = `
        <div class="barbers-grid">
            ${statCard("Успешни", e.success_24h, "var(--success)")}
            ${statCard("Неуспешни", e.failed_24h, "#e06b62")}
        </div>
    `;

    const container = document.getElementById("emailFailures");

    if (!e.recent_failures || e.recent_failures.length === 0) {
        container.innerHTML = "<p style='color:var(--text-sub);font-size:12px;'>Няма скорошни грешки</p>";
        return;
    }

    container.innerHTML = "<h3 style='margin-bottom:10px;'>Последни грешки</h3>" + e.recent_failures.map(f => `
        <div class="card" style="width:100%; text-align:left; display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div>
                <strong style="color:#e06b62;">${f.to_email}</strong> — ${f.status_type || "-"}<br>
                <span style="font-size:11px;color:var(--text-sub);">${f.error || ""}</span>
            </div>
            <span style="font-size:11px;color:var(--text-muted);">${f.created_at}</span>
        </div>
    `).join('');
}

function renderActivity(list) {
    const container = document.getElementById("activityLog");

    if (!list || list.length === 0) {
        container.innerHTML = "<p style='color:var(--text-sub);font-size:12px;'>Няма активност</p>";
        return;
    }

    container.innerHTML = list.map(l => `
        <div class="card" style="width:100%; text-align:left; margin-bottom:6px;">
            <strong>${l.action}</strong><br>
            <span style="font-size:12px;color:var(--text-sub);">${l.description || ""}</span><br>
            <span style="font-size:11px;color:var(--text-muted);">${l.created_at}</span>
        </div>
    `).join('');
}

function logout() {
    fetch('/logout').then(() => window.location = "/login");
}

load();
setInterval(load, 15000);