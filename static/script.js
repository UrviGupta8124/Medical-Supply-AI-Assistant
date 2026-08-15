// Client-side API fetch logic
const API_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    const tableSelect = document.getElementById("select-table");
    const gridContainer = document.getElementById("grid-container");
    const chatInput = document.getElementById("chat-input");
    const btnSend = document.getElementById("btn-send");
    const chatMessages = document.getElementById("chat-messages");

    tableSelect.addEventListener("change", async (e) => {
        const tableName = e.target.value;
        const res = await fetch(`${API_URL}/api/admin/tables/${tableName}`);
        const data = await res.json();
        
        if (data.rows) {
            let html = `<table><thead><tr>`;
            data.columns.forEach(col => html += `<th>${col}</th>`);
            html += `</tr></thead><tbody>`;
            data.rows.forEach(row => {
                html += `<tr>`;
                data.columns.forEach(col => html += `<td>${row[col] || ''}</td>`);
                html += `</tr>`;
            });
            html += `</tbody></table>`;
            gridContainer.innerHTML = html;
        }
    });

    btnSend.addEventListener("click", async () => {
        const message = chatInput.value.trim();
        if (!message) return;

        appendMessage("user", message);
        chatInput.value = "";

        const res = await fetch(`${API_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, language: "en" })
        });
        const data = await res.json();
        appendMessage("bot", data.reply);
    });

    function appendMessage(sender, text) {
        const div = document.createElement("div");
        div.className = `message ${sender}`;
        div.innerText = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
