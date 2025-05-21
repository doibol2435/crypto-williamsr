const socket = io();

socket.on("update_signals", (data) => {
    const container = document.getElementById("signal-container");
    container.innerHTML = "";

    for (const [symbol, signal] of Object.entries(data)) {
        const card = document.createElement("div");
        card.className = "signal-card";

        if (signal.signal === "Long") card.classList.add("long");
        if (signal.signal === "Short") card.classList.add("short");

        card.innerHTML = `
            <b>${symbol}</b><br>
            Tín hiệu: ${signal.signal || "Không có"}<br>
            %R: ${signal.williams_r || "-"}<br>
            Entry: ${signal.entry || "-"}<br>
            TP: ${signal.tp || "-"}<br>
            SL: ${signal.sl || "-"}
        `;
        container.appendChild(card);
    }
});
