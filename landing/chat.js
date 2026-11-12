/* Hero chat — talks to POST /api/chat on this same origin */
(function () {
  const root = document.getElementById("nm-chat");
  if (!root) return;

  const messagesEl = root.querySelector(".nm-chat__messages");
  const form = root.querySelector(".nm-chat__form");
  const input = root.querySelector(".nm-chat__input");
  const sendBtn = root.querySelector(".nm-chat__send");

  /** OpenAI-style history shown to the user (and sent to the API). */
  const history = [];

  function appendBubble(role, text) {
    const div = document.createElement("div");
    div.className =
      "nm-msg " + (role === "user" ? "nm-msg--user" : "nm-msg--bot");
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function appendError(text) {
    const div = document.createElement("div");
    div.className = "nm-msg nm-msg--error";
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "nm-msg nm-msg--typing";
    div.setAttribute("aria-label", "Assistant is typing");
    div.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  async function send(text) {
    history.push({ role: "user", content: text });
    appendBubble("user", text);

    input.value = "";
    sendBtn.disabled = true;
    input.disabled = true;
    const typing = showTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });
      typing.remove();

      if (!res.ok) {
        let detail = "Request failed (" + res.status + ")";
        try {
          const err = await res.json();
          if (err.detail) detail = String(err.detail);
        } catch (_) { /* keep default */ }
        history.pop(); // retry-able: drop failed user turn
        appendError(detail);
        return;
      }

      const data = await res.json();
      const reply = data.reply || "(no response)";
      history.push({ role: "assistant", content: reply });
      appendBubble("assistant", reply);
    } catch (e) {
      typing.remove();
      history.pop();
      appendError("Network error — is the server running?");
      console.error(e);
    } finally {
      sendBtn.disabled = false;
      input.disabled = false;
      input.focus();
    }
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text || sendBtn.disabled) return;
    send(text);
  });

  // Safety net: Webflow's entrance animation starts this wrapper at
  // opacity:0 — if interactions never fire, force it visible.
  const wrapper = root.closest(".header-2-image-wrapper");
  if (wrapper) {
    setTimeout(function () {
      if (getComputedStyle(wrapper).opacity === "0") {
        wrapper.style.opacity = "1";
        wrapper.style.transform = "none";
      }
    }, 1200);
  }

  input.focus();
})();
