self.addEventListener('push', function (event) {
    console.log("🔥 PUSH RECEIVED");

    let data = {
        title: "Нова заявка",
        body: "Имате нов запис"
    };

    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) { }
    }

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/barbericon.jpg'
        })
    );
});