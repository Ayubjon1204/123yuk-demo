(() => {
  const loader = document.currentScript;
  const configuredBase = (loader && loader.dataset.apiBaseUrl) || "";
  const tag = "yuk-support-widget";

  if (customElements.get(tag)) return;

  class YukSupportWidget extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this.history = [];
      this.busy = false;
      this.render();
    }

    connectedCallback() {
      this.launcher = this.shadowRoot.querySelector(".launcher");
      this.panel = this.shadowRoot.querySelector(".panel");
      this.closeButton = this.shadowRoot.querySelector(".close");
      this.resetButton = this.shadowRoot.querySelector(".reset");
      this.form = this.shadowRoot.querySelector("form");
      this.input = this.shadowRoot.querySelector("textarea");
      this.messages = this.shadowRoot.querySelector(".messages");
      this.status = this.shadowRoot.querySelector(".status");
      this.launcher.addEventListener("click", () => this.open());
      this.closeButton.addEventListener("click", () => this.close());
      this.resetButton.addEventListener("click", () => this.reset());
      this.form.addEventListener("submit", (event) => this.submit(event));
      this.input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          this.form.requestSubmit();
        }
      });
      this.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !this.panel.hidden) this.close();
      });
      this.apiBase = this.getAttribute("api-base-url") || configuredBase;
    }

    render() {
      const root = this.shadowRoot;
      root.innerHTML = `
        <style>
          :host{all:initial;--yuk-blue:#1d4ed8;--yuk-ink:#172033;--yuk-muted:#64748b;--yuk-line:#e2e8f0;--yuk-bg:#fff;--yuk-shadow:0 18px 55px #0f172a2b;font-family:Inter,Arial,sans-serif;color:var(--yuk-ink);font-size:14px;line-height:1.45}
          *{box-sizing:border-box}button,textarea{font:inherit}button{cursor:pointer}
          .launcher{position:fixed;z-index:2147483000;right:22px;bottom:22px;width:58px;height:58px;border:0;border-radius:50%;background:var(--yuk-blue);color:#fff;box-shadow:var(--yuk-shadow);font-size:25px}
          .panel{position:fixed;z-index:2147483000;right:22px;bottom:92px;width:min(370px,calc(100vw - 28px));height:min(550px,calc(100dvh - 120px));min-height:360px;background:var(--yuk-bg);border:1px solid var(--yuk-line);border-radius:18px;box-shadow:var(--yuk-shadow);display:flex;flex-direction:column;overflow:hidden}
          .panel[hidden]{display:none}.head{padding:15px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--yuk-line)}
          .title{font-weight:700;flex:1}.subtitle{display:block;font-size:12px;color:var(--yuk-muted);font-weight:400}.head button{border:0;background:transparent;border-radius:8px;padding:7px;color:var(--yuk-ink)}.head button:hover{background:#f1f5f9}
          .notice{padding:9px 13px;background:#eff6ff;color:#1e3a8a;font-size:11px;border-bottom:1px solid #dbeafe}
          .messages{padding:14px;flex:1;overflow:auto;display:flex;flex-direction:column;gap:9px}.bubble{max-width:90%;white-space:pre-wrap;overflow-wrap:anywhere;padding:10px 12px;border-radius:12px;background:#f1f5f9;color:var(--yuk-ink)}.bubble.user{align-self:flex-end;background:#dbeafe}.bubble.assistant{align-self:flex-start}.bubble.error{background:#fef2f2;color:#991b1b}
          .status{min-height:18px;padding:0 14px;color:var(--yuk-muted);font-size:12px}.composer{padding:11px;border-top:1px solid var(--yuk-line);display:flex;gap:8px;align-items:flex-end}.composer textarea{flex:1;resize:vertical;min-height:42px;max-height:120px;border:1px solid #cbd5e1;border-radius:10px;padding:10px;color:var(--yuk-ink);background:#fff}.composer textarea:focus-visible,button:focus-visible{outline:3px solid #93c5fd;outline-offset:2px}.send{border:0;border-radius:10px;background:var(--yuk-blue);color:#fff;height:42px;padding:0 14px;font-weight:600}.send:disabled{opacity:.55;cursor:wait}
          @media(max-width:480px){.launcher{right:14px;bottom:14px}.panel{right:8px;bottom:82px;width:calc(100vw - 16px);height:min(620px,calc(100dvh - 96px));min-height:300px}}
          @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
        </style>
        <button class="launcher" type="button" aria-label="123YUK yordam chatini ochish" aria-controls="support-panel" aria-expanded="false">?</button>
        <section class="panel" id="support-panel" role="dialog" aria-modal="false" aria-label="123YUK yordam" hidden>
          <header class="head"><div class="title">123YUK yordam<span class="subtitle">Zavod tizimi bo‘yicha savol bering</span></div><button class="reset" type="button" aria-label="Suhbatni tozalash">↻</button><button class="close" type="button" aria-label="Yordam chatini yopish">×</button></header>
          <div class="notice">Demo backend ma’lumoti haqiqiy dashboard bilan sinxron emas.</div>
          <div class="messages" role="log" aria-live="polite" aria-relevant="additions text"></div>
          <div class="status" aria-live="polite"></div>
          <form class="composer"><label class="sr-only" for="yuk-support-message">Xabaringiz</label><textarea id="yuk-support-message" maxlength="2000" rows="1" placeholder="Savolingizni yozing…" required></textarea><button class="send" type="submit">Yuborish</button></form>
        </section>`;
      const style = document.createElement("style");
      style.textContent = ".sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}";
      root.append(style);
    }

    open() {
      this.panel.hidden = false;
      this.launcher.setAttribute("aria-expanded", "true");
      this.input.focus();
    }

    close() {
      this.panel.hidden = true;
      this.launcher.setAttribute("aria-expanded", "false");
      this.launcher.focus();
    }

    reset() {
      this.history = [];
      this.messages.replaceChildren();
      this.status.textContent = "Suhbat tozalandi.";
      this.input.value = "";
      this.input.focus();
    }

    addMessage(role, text, kind = "") {
      const bubble = document.createElement("div");
      bubble.className = `bubble ${role} ${kind}`.trim();
      bubble.textContent = text;
      this.messages.append(bubble);
      this.messages.scrollTop = this.messages.scrollHeight;
      return bubble;
    }

    async submit(event) {
      event.preventDefault();
      const message = this.input.value.trim();
      if (!message || this.busy) return;
      const previous = this.history.slice(-12);
      this.addMessage("user", message);
      this.history.push({ role: "user", content: message });
      this.input.value = "";
      this.busy = true;
      const send = this.shadowRoot.querySelector(".send");
      send.disabled = true;
      this.panel.setAttribute("aria-busy", "true");
      this.status.textContent = "Javob tayyorlanmoqda…";
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 20000);
      try {
        if (!this.apiBase) throw new Error("API_NOT_CONFIGURED");
        const response = await fetch(`${this.apiBase.replace(/\/$/, "")}/api/v1/assistant/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history: previous }),
          signal: controller.signal,
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload?.error?.code || "API_ERROR");
        const answer = typeof payload.message === "string" ? payload.message : "Bu ma’lumot hozircha mavjud manbalarda topilmadi.";
        this.addMessage("assistant", answer);
        this.history.push({ role: "assistant", content: answer });
        const aiStatus = {
          disabled: "AI xizmati o‘chiq; lokal FAQ va parking hisoblari ishlaydi.",
          not_configured: "Bepul AI sozlanmagan; lokal FAQ va parking hisoblari ishlaydi.",
          unavailable: "AI xizmati hozir mavjud emas; lokal FAQ va parking hisoblari ishlaydi.",
          quota_exceeded: "Bepul AI limiti tugadi; lokal FAQ va parking hisoblari ishlaydi.",
          timeout: "AI javobini kutish vaqti tugadi; lokal FAQ va parking hisoblari ishlaydi.",
          provider_error: "AI xizmati xato qaytardi; lokal FAQ va parking hisoblari ishlaydi.",
        };
        this.status.textContent = Object.hasOwn(aiStatus, payload.ai_status) ? aiStatus[payload.ai_status] : "";
      } catch (error) {
        const text = error.name === "AbortError"
          ? "So‘rov vaqti tugadi. Birozdan so‘ng qayta urinib ko‘ring."
          : error.message === "API_NOT_CONFIGURED"
            ? "Yordam serveri ulanmagan. Lokal backend manzilini sozlang."
            : "Yordam xizmati hozir javob bermayapti. Keyinroq qayta urinib ko‘ring.";
        this.addMessage("assistant", text, "error");
        this.status.textContent = "Xatolik";
      } finally {
        window.clearTimeout(timeout);
        this.busy = false;
        send.disabled = false;
        this.panel.setAttribute("aria-busy", "false");
        this.input.focus();
      }
    }
  }

  customElements.define(tag, YukSupportWidget);
  const widget = document.createElement(tag);
  document.body.append(widget);
})();
