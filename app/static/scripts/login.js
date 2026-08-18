fetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username,
        password
    })
})
    .then(r => r.json())
    .then(res => {
        if (res.error) {
            alert(res.error);
            return;
        }

        window.location = res.redirect;  // 🔥
    });