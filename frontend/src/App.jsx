import { useEffect, useState } from "react";
import { DATA_UPDATED } from "./config.js";
import { fmtDate } from "./lib/loan.js";
import { getReply } from "./lib/api.js";
import { Icon, Orb } from "./components/icons.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Welcome from "./components/Welcome.jsx";
import Messages, { errorInfo } from "./components/Messages.jsx";
import Composer from "./components/Composer.jsx";
import LoanForm, { EMPTY_LOAN_FORM } from "./components/LoanForm.jsx";
import Home from "./components/Home.jsx";
import { ConfirmClearDialog, Drawer, HistoryDialog, SettingsDialog } from "./components/Dialogs.jsx";
import { DEFAULT_SETTINGS, FONT_SIZES, clearSettings, loadSettings, saveSettings } from "./lib/settings.js";

const uid = () => crypto.randomUUID();
// Màn hiện tại nằm trên địa chỉ (#/, #/tro-chuyen) để nút Back của trình duyệt dùng được.
// Công cụ tính khoản vay là bảng trượt bên phải, mở chồng lên trang chủ hoặc màn chat.
const ROUTES = { home: "#/", chat: "#/tro-chuyen" };
const viewFromHash = () => Object.keys(ROUTES).find((k) => ROUTES[k] === window.location.hash) ?? "home";
// Form mới (hoặc sau khi xóa dữ liệu) lấy phương thức và lãi suất mặc định từ Cài đặt
const emptyForm = (s) => ({ ...EMPTY_LOAN_FORM, method: s.method, rate: String(s.rate).replace(".", ",") });
const clock = () => new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });

export default function App() {
  const [convos, setConvos] = useState([]);   // { id, title, updatedAt, messages[] }, chỉ lưu trong bộ nhớ, không lưu trình duyệt
  const [activeId, setActiveId] = useState(null);
  const [pendingId, setPendingId] = useState(null);
  const [draft, setDraft] = useState("");
  const [menu, setMenu] = useState(false);
  const [view, setViewState] = useState(viewFromHash); // "home" | "chat"
  const [formOpen, setFormOpen] = useState(false); // bảng Công cụ tính khoản vay
  const [settings, setSettings] = useState(loadSettings); // cài đặt thì lưu trình duyệt (xem lib/settings.js)
  const [loanForm, setLoanForm] = useState(() => emptyForm(settings)); // chỉ giữ trong bộ nhớ như hội thoại
  const [collapsed, setCollapsed] = useState(false); // thanh bên thu gọn trên màn hình rộng
  const [dialog, setDialog] = useState(null); // "history" | "settings" | "clear" | null

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
  const push = (id, m) => setConvos((cs) => cs.map((c) => (c.id === id ? { ...c, updatedAt: Date.now(), messages: [...c.messages, { id: uid(), ...m }] } : c)));

  async function ask(id, text) {
    setPendingId(id);
    try {
      const r = await getReply({ message: text, sessionId: id });
      push(id, { role: "bot", text: r.reply, estimate: r.estimate, updatedAt: r.updated_at });
    } catch (err) {
      const code = err?.code ?? "UNKNOWN";
      const [title, detail] = errorInfo(code);
      push(id, { role: "bot", text: `${title}. ${detail}`, error: true, code, time: clock(), question: text });
    } finally {
      setPendingId((p) => (p === id ? null : p));
    }
  }

  // fresh: mở cuộc trò chuyện mới (gửi từ trang chủ) thay vì nối vào cuộc đang mở
  function send(raw, fresh = false) {
    const text = raw.trim();
    if (!text || (loading && !fresh)) return;
    let id = fresh ? null : activeId;
    if (!id) {
      id = uid();
      const title = text.length > 40 ? text.slice(0, 40) + "..." : text;
      setConvos((cs) => [{ id, title, updatedAt: Date.now(), messages: [{ id: uid(), role: "user", text }] }, ...cs]);
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
    setFormOpen(true);
    setMenu(false);
  };
  // Trong chat thì gửi vào cuộc đang mở; từ trang chủ thì sang chat và mở cuộc mới
  const inChat = view === "chat" && active !== null;
  const askFromForm = (text) => { setFormOpen(false); setView("chat"); send(text, !inChat); };
  const openDialog = (name) => { setMenu(false); setDialog(name); };
  const clearAll = () => {
    setConvos([]); setActiveId(null); setPendingId(null); setDraft(""); setMenu(false); setDialog(null);
    clearSettings(); setSettings(DEFAULT_SETTINGS); setLoanForm(emptyForm(DEFAULT_SETTINGS));
  };
  const applySettings = (s) => {
    setSettings(s); saveSettings(s); setDialog(null);
    // Form chưa nhập gì thì đổi luôn theo mặc định mới
    setLoanForm((f) => (f.amount === "" && f.bankId === "" ? { ...f, method: s.method, rate: String(s.rate).replace(".", ",") } : f));
  };
  const lastMsg = active?.messages.at(-1);
  const failing = view === "chat" && lastMsg?.error ? lastMsg.code : null;

  const dialogs = (
    <>
      <Drawer open={formOpen} onClose={() => setFormOpen(false)} labelledBy="loan-title">
        <LoanForm values={loanForm} onChange={setLoanForm} empty={emptyForm(settings)} onClose={() => setFormOpen(false)}
          onAsk={askFromForm} askLabel={inChat ? "Gửi kết quả vào cuộc trò chuyện" : "Hỏi trợ lý AI về khoản vay này"} />
      </Drawer>
      <HistoryDialog open={dialog === "history"} onClose={() => setDialog(null)} convos={convos} activeId={activeId}
        onSelect={(id) => { setActiveId(id); setDialog(null); setView("chat"); }} />
      <SettingsDialog open={dialog === "settings"} onClose={() => setDialog(null)} value={settings} onSave={applySettings} />
      <ConfirmClearDialog open={dialog === "clear"} onClose={() => setDialog(null)} onConfirm={clearAll} count={convos.length} />
    </>
  );

  if (view === "home") return <><Home onChat={() => setView("chat")} onForm={() => openForm()} />{dialogs}</>;

  const composer = <Composer value={draft} onChange={setDraft} onSend={() => send(draft)} disabled={loading} />;

  return (
    <div className="h-dvh" style={{ "--chat-fs": `${FONT_SIZES[settings.fontSize]}px` }}>
      <div className="flex h-full gap-3 p-2 sm:p-3" style={{ background: "linear-gradient(135deg,#F3FAD6,#DCF3E6)" }}>
        <Sidebar convos={convos} activeId={view === "chat" ? activeId : null} open={menu} onClose={() => setMenu(false)} onNew={newChat}
          onSelect={(id) => { setActiveId(id); setMenu(false); setView("chat"); }} onClear={() => openDialog("clear")}
          onHome={() => { setMenu(false); setView("home"); }}
          collapsed={collapsed} onToggleCollapse={() => setCollapsed((c) => !c)}
          onHistory={() => openDialog("history")} onSettings={() => openDialog("settings")} />

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
            {failing ? (
              <p className="flex items-center gap-2 rounded-full border border-[#f1c9c6] bg-[#fdf1f0] px-3.5 py-2 text-[13px] text-[#c0443f]">
                <span className="size-1.5 rounded-full bg-[#c0443f]" aria-hidden="true" />
                {failing === "NETWORK_ERROR" ? "Mất kết nối máy chủ" : "Máy chủ đang lỗi"}
              </p>
            ) : (
              <p className="flex items-center gap-2 rounded-full border border-line bg-white px-3.5 py-2 text-[13px] text-muted">
                <span className="size-1.5 rounded-full bg-[#4fc47a]" aria-hidden="true" />
                <span><span className="hidden sm:inline">Dữ liệu </span>cập nhật {fmtDate(lastBot?.updatedAt ?? DATA_UPDATED)}</span>
              </p>
            )}
          </header>

          {active ? (
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
      {dialogs}
    </div>
  );
}
