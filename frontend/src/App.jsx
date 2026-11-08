import { useEffect, useState } from "react";
import { DATA_UPDATED } from "./config.js";
import { fmtDate } from "./lib/loan.js";
import { getReply } from "./lib/api.js";
import { Icon, Orb } from "./components/icons.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Welcome from "./components/Welcome.jsx";
import Messages from "./components/Messages.jsx";
import Composer from "./components/Composer.jsx";
import LoanForm, { EMPTY_LOAN_FORM } from "./components/LoanForm.jsx";
import Home from "./components/Home.jsx";

const uid = () => crypto.randomUUID();
// Màn hiện tại nằm trên địa chỉ (#/tro-chuyen, #/nhap-thong-tin) để nút Back của trình duyệt dùng được
const ROUTES = { home: "#/", chat: "#/tro-chuyen", form: "#/nhap-thong-tin" };
const viewFromHash = () => Object.keys(ROUTES).find((k) => ROUTES[k] === window.location.hash) ?? "home";
const ERROR_TEXT = "Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy và địa chỉ API trong file .env, rồi gửi lại.";

export default function App() {
  const [convos, setConvos] = useState([]);   // { id, title, messages[] }, chỉ lưu trong bộ nhớ, không lưu trình duyệt
  const [activeId, setActiveId] = useState(null);
  const [pendingId, setPendingId] = useState(null);
  const [draft, setDraft] = useState("");
  const [menu, setMenu] = useState(false);
  const [view, setViewState] = useState(viewFromHash); // "home" | "chat" | "form"
  const [loanForm, setLoanForm] = useState(EMPTY_LOAN_FORM); // chỉ giữ trong bộ nhớ như hội thoại

  useEffect(() => {
    const onHash = () => setViewState(viewFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const setView = (v) => {
    setViewState(v);
    if (window.location.hash !== ROUTES[v]) window.location.hash = ROUTES[v];
  };

  const active = convos.find((c) => c.id === activeId) ?? null;
  const loading = pendingId !== null && pendingId === activeId;
  const lastBot = active ? [...active.messages].reverse().find((m) => m.role === "bot" && m.updatedAt) : null;

  const patch = (id, fn) => setConvos((cs) => cs.map((c) => (c.id === id ? { ...c, messages: fn(c.messages) } : c)));
  const push = (id, m) => patch(id, (ms) => [...ms, { id: uid(), ...m }]);

  async function ask(id, text) {
    setPendingId(id);
    try {
      const r = await getReply({ message: text, sessionId: id });
      push(id, { role: "bot", text: r.reply, estimate: r.estimate, updatedAt: r.updated_at });
    } catch {
      push(id, { role: "bot", text: ERROR_TEXT, error: true });
    } finally {
      setPendingId((p) => (p === id ? null : p));
    }
  }

  function send(raw) {
    const text = raw.trim();
    if (!text || loading) return;
    let id = activeId;
    if (!id) {
      id = uid();
      const title = text.length > 40 ? text.slice(0, 40) + "..." : text;
      setConvos((cs) => [{ id, title, messages: [{ id: uid(), role: "user", text }] }, ...cs]);
      setActiveId(id);
    } else {
      push(id, { role: "user", text });
    }
    setDraft("");
    ask(id, text);
  }

  function regenerate() {
    if (!active || loading) return;
    const idx = active.messages.map((m) => m.role).lastIndexOf("user");
    if (idx < 0) return;
    const text = active.messages[idx].text;
    patch(active.id, (ms) => ms.slice(0, idx + 1));
    ask(active.id, text);
  }

  const rate = (msgId, v) => patch(active.id, (ms) => ms.map((m) => (m.id === msgId ? { ...m, rating: m.rating === v ? null : v } : m)));
  const newChat = () => { setActiveId(null); setDraft(""); setMenu(false); setView("chat"); };
  const openForm = (estimate) => {
    if (estimate) {
      setLoanForm((f) => ({ ...f, amount: String(Math.round(estimate.amount)), years: String(estimate.years),
        method: estimate.method ?? f.method, bankId: "", rate: String(estimate.rate ?? f.rate).replace(".", ",") }));
    }
    setView("form");
    setMenu(false);
  };
  const clearAll = () => {
    if (window.confirm("Xóa toàn bộ cuộc trò chuyện trên trình duyệt này?")) { setConvos([]); setActiveId(null); setPendingId(null); setDraft(""); setMenu(false); setLoanForm(EMPTY_LOAN_FORM); }
  };

  if (view === "home") return <Home onChat={() => setView("chat")} onForm={() => openForm()} />;

  const composer = <Composer value={draft} onChange={setDraft} onSend={() => send(draft)} disabled={loading} />;

  return (
    <div className="h-dvh">
      <div className="flex h-full gap-3 p-2 sm:p-3" style={{ background: "linear-gradient(135deg,#F3FAD6,#DCF3E6)" }}>
        <Sidebar convos={convos} activeId={view === "chat" ? activeId : null} open={menu} onClose={() => setMenu(false)} onNew={newChat}
          onSelect={(id) => { setActiveId(id); setMenu(false); setView("chat"); }} onClear={clearAll}
          formActive={view === "form"} onForm={() => openForm()} onHome={() => { setMenu(false); setView("home"); }} />

        <main className="dots flex min-w-0 flex-1 flex-col rounded-[22px] bg-white">
          <header className="flex items-center justify-between gap-3 px-4 py-4 sm:px-6">
            <div className="flex items-center gap-2.5">
              <button onClick={() => setMenu(true)} aria-label="Mở thanh bên" className="-ml-1 rounded-lg p-1.5 text-muted focus-visible:outline-2 focus-visible:outline-brand lg:hidden">
                <Icon name="menu" size={20} />
              </button>
              <button onClick={() => setView("home")} title="Về trang chủ" aria-label="Trợ lý vay mua nhà, về trang chủ" className="flex items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">
                <Orb size={28} />
                <span className="text-[15px] font-medium">Trợ lý vay mua nhà</span>
              </button>
            </div>
            <p className="flex items-center gap-2 rounded-full border border-line bg-white px-3.5 py-2 text-[13px] text-muted">
              <span className="size-1.5 rounded-full bg-[#4fc47a]" aria-hidden="true" />
              <span><span className="hidden sm:inline">Dữ liệu </span>cập nhật {fmtDate(lastBot?.updatedAt ?? DATA_UPDATED)}</span>
            </p>
          </header>

          {view === "form" ? (
            <LoanForm values={loanForm} onChange={setLoanForm} onBack={() => setView("chat")}
              onAsk={(text) => { setView("chat"); send(text); }} />
          ) : active ? (
            <>
              <Messages messages={active.messages} loading={loading} onRate={rate} onRegenerate={regenerate}
                onAsk={send} onAdjust={openForm} />
              <div className="px-4 pb-5 pt-2 sm:px-8 sm:pb-6">{composer}</div>
            </>
          ) : (
            <Welcome onPick={send} onForm={() => openForm()}>{composer}</Welcome>
          )}
        </main>
      </div>
    </div>
  );
}
