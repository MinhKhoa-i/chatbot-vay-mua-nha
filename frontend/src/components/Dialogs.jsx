import { useEffect, useRef, useState } from "react";
import { validRate } from "../lib/settings.js";
import { Icon } from "./icons.jsx";

// Hộp thoại dùng thẻ <dialog> của trình duyệt: tự giữ focus bên trong, Esc để đóng, có lớp phủ.
function useModal(open, onClose) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return {
    ref,
    onCancel: (e) => { e.preventDefault(); onClose(); },
    onClick: (e) => { if (e.target === e.currentTarget) onClose(); }, // bấm ra lớp phủ thì đóng
  };
}

function Dialog({ open, onClose, labelledBy, width, children }) {
  const modal = useModal(open, onClose);
  return (
    <dialog {...modal} aria-labelledby={labelledBy}
      className={`m-auto max-h-[calc(100dvh-32px)] w-[calc(100vw-32px)] overflow-y-auto rounded-[24px] bg-white p-0 text-ink shadow-2xl backdrop:bg-[#161816]/35 ${width}`}>
      {open && <div className="p-6 sm:p-7">{children}</div>}
    </dialog>
  );
}

// Bảng trượt ra từ cạnh phải (Công cụ tính khoản vay, V3 - 8); điện thoại thì chiếm cả màn hình
export function Drawer({ open, onClose, labelledBy, children }) {
  const modal = useModal(open, onClose);
  return (
    <dialog {...modal} aria-labelledby={labelledBy}
      className="fixed inset-y-0 left-auto right-0 m-0 h-dvh max-h-dvh w-full max-w-full overflow-hidden bg-white p-0 text-ink shadow-2xl backdrop:bg-[#161816]/25 sm:inset-y-3 sm:right-3 sm:h-[calc(100dvh-24px)] sm:max-h-[calc(100dvh-24px)] sm:w-[480px] sm:rounded-[22px]">
      {open && children}
    </dialog>
  );
}

function Head({ id, title, sub, onClose }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h2 id={id} className="text-[22px] font-medium leading-tight">{title}</h2>
        {sub && <p className="mt-1 text-[13px] text-muted">{sub}</p>}
      </div>
      <button onClick={onClose} aria-label="Đóng" className="grid size-9 shrink-0 place-items-center rounded-full border border-line text-muted hover:bg-soft focus-visible:outline-2 focus-visible:outline-brand">
        <Icon name="close" size={16} />
      </button>
    </div>
  );
}

// ---- V3 - 11. Lịch sử trò chuyện ----
const fold = (s) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/đ/gi, "d").toLowerCase();
const dayStart = (t) => new Date(new Date(t).toDateString()).getTime();
const hhmm = (t) => new Date(t).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
const ddmm = (t) => new Date(t).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });

function groupByDay(convos) {
  const today = dayStart(Date.now());
  const label = (t) => {
    const d = dayStart(t);
    if (d === today) return "Hôm nay";
    if (d === today - 86400000) return "Hôm qua";
    return "Trước đó";
  };
  const groups = [];
  for (const c of [...convos].sort((a, b) => b.updatedAt - a.updatedAt)) {
    const name = label(c.updatedAt);
    if (groups.at(-1)?.name !== name) groups.push({ name, items: [] });
    groups.at(-1).items.push(c);
  }
  return groups;
}

export function HistoryDialog({ open, onClose, convos, activeId, onSelect }) {
  const [q, setQ] = useState("");
  useEffect(() => { if (open) setQ(""); }, [open]);
  const key = fold(q.trim());
  const found = key ? convos.filter((c) => fold(c.title).includes(key) || c.messages.some((m) => !m.error && fold(m.text).includes(key))) : convos;
  const today = dayStart(Date.now());

  return (
    <Dialog open={open} onClose={onClose} labelledBy="ls-title" width="max-w-[580px]">
      <Head id="ls-title" title="Lịch sử trò chuyện" onClose={onClose} />
      <label className="mt-5 flex items-center gap-2.5 rounded-xl border border-line px-3.5 py-2.5 focus-within:border-brand">
        <Icon name="search" size={17} className="text-muted" />
        <span className="sr-only">Tìm trong lịch sử trò chuyện</span>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm trong lịch sử trò chuyện"
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted" />
      </label>

      <div className="mt-4 flex flex-col gap-4">
        {convos.length === 0 ? (
          <p className="px-2.5 py-6 text-center text-sm text-muted">Chưa có cuộc trò chuyện nào.</p>
        ) : found.length === 0 ? (
          <p className="px-2.5 py-6 text-center text-sm text-muted">Không tìm thấy cuộc trò chuyện phù hợp.</p>
        ) : groupByDay(found).map((g) => (
          <section key={g.name} aria-label={g.name}>
            <h3 className="px-2.5 text-xs font-medium text-muted">{g.name}</h3>
            <ul className="mt-1 flex flex-col">
              {g.items.map((c) => (
                <li key={c.id}>
                  <button onClick={() => onSelect(c.id)} aria-current={c.id === activeId ? "true" : undefined}
                    className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2.5 text-left hover:bg-soft focus-visible:outline-2 focus-visible:outline-brand ${c.id === activeId ? "bg-soft" : ""}`}>
                    <span className="grid size-[34px] shrink-0 place-items-center rounded-full bg-soft text-muted"><Icon name="chat" size={16} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{c.title}</span>
                      <span className="block text-xs text-muted">
                        {dayStart(c.updatedAt) === today ? hhmm(c.updatedAt) : ddmm(c.updatedAt)} · {c.messages.length} tin nhắn
                      </span>
                    </span>
                    <Icon name="chevRight" size={16} className="text-faint" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <p className="mt-5 flex gap-2.5 rounded-xl bg-soft px-3.5 py-3 text-[13px] leading-relaxed text-muted">
        <Icon name="info" size={16} className="mt-0.5 shrink-0" />
        Lịch sử chỉ lưu tạm trong tab trình duyệt này, tải lại trang là mất. Dùng “Xóa dữ liệu của tôi” để xóa ngay.
      </p>
    </Dialog>
  );
}

// ---- V3 - 12. Cài đặt ----
const FONT_OPTIONS = [["sm", "Nhỏ"], ["md", "Vừa"], ["lg", "Lớn"]];
const METHOD_OPTIONS = [["annuity", "Trả đều gốc + lãi"], ["reducing_balance", "Gốc đều, lãi giảm dần"]];
const rateText = (r) => String(r).replace(".", ",");

function Row({ id, label, hint, children }) {
  return (
    <div className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="sm:max-w-[250px]">
        <p id={id} className="text-[15px] font-medium">{label}</p>
        {hint && <p className="mt-0.5 text-[13px] leading-snug text-muted">{hint}</p>}
      </div>
      <div className="sm:w-[270px] sm:shrink-0">{children}</div>
    </div>
  );
}

export function SettingsDialog({ open, onClose, value, onSave }) {
  const [fontSize, setFontSize] = useState(value.fontSize);
  const [method, setMethod] = useState(value.method);
  const [rate, setRate] = useState(rateText(value.rate));
  const [error, setError] = useState("");
  useEffect(() => {
    if (!open) return;
    setFontSize(value.fontSize); setMethod(value.method); setRate(rateText(value.rate)); setError("");
  }, [open, value]);

  const save = (e) => {
    e.preventDefault();
    const r = rate.trim() === "" ? NaN : Number(rate.replace(",", "."));
    if (!validRate(r)) { setError("Lãi suất từ 0 đến 30%/năm, ví dụ 8,5."); return; }
    onSave({ fontSize, method, rate: r });
  };

  return (
    <Dialog open={open} onClose={onClose} labelledBy="st-title" width="max-w-[600px]">
      <form onSubmit={save} noValidate>
        <Head id="st-title" title="Cài đặt" sub="Áp dụng cho trình duyệt này." onClose={onClose} />

        <div className="mt-4 border-b border-line pb-2">
          <Row id="st-fs" label="Cỡ chữ" hint="Cỡ chữ của tin nhắn trong khung chat.">
            <fieldset aria-labelledby="st-fs" className="flex rounded-xl bg-soft p-1">
              {FONT_OPTIONS.map(([k, l]) => (
                <label key={k} className={`flex-1 cursor-pointer rounded-[10px] py-2 text-center text-sm has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-brand ${fontSize === k ? "bg-white font-medium shadow-sm" : "text-muted hover:text-ink"}`}>
                  <input type="radio" name="st-fs" value={k} checked={fontSize === k} onChange={() => setFontSize(k)} className="sr-only" />
                  {l}
                </label>
              ))}
            </fieldset>
          </Row>
        </div>

        <div className="pt-2">
          <Row id="st-method" label="Phương thức trả nợ mặc định" hint="Điền sẵn khi bạn mở form nhập thông tin khoản vay.">
            <div className="relative">
              <select aria-labelledby="st-method" value={method} onChange={(e) => setMethod(e.target.value)}
                className="w-full appearance-none rounded-xl border border-line bg-white px-3.5 py-2.5 pr-10 text-sm outline-none focus:border-brand">
                {METHOD_OPTIONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
              <Icon name="chev" size={16} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-muted" />
            </div>
          </Row>
          <Row id="st-rate" label="Lãi suất giả định mặc định" hint="Điền sẵn vào form, luôn được ghi rõ là lãi suất giả định.">
            <div className={`flex items-center rounded-xl border px-3.5 py-2.5 focus-within:border-brand ${error ? "border-[#c0443f]" : "border-line"}`}>
              <input aria-labelledby="st-rate" inputMode="decimal" value={rate} aria-invalid={!!error} aria-describedby={error ? "st-rate-err" : undefined}
                onChange={(e) => { setRate(e.target.value.replace(/[^\d.,]/g, "").slice(0, 6)); setError(""); }}
                className="min-w-0 flex-1 bg-transparent text-sm outline-none" />
              <span className="text-sm text-muted">%/năm</span>
            </div>
            {error && <p id="st-rate-err" className="mt-1.5 text-[13px] text-[#c0443f]">{error}</p>}
          </Row>
        </div>

        <div className="mt-5 flex justify-end gap-2.5">
          <button type="button" onClick={onClose} className="rounded-xl border border-line px-5 py-3 text-sm font-medium hover:bg-soft focus-visible:outline-2 focus-visible:outline-brand">Hủy</button>
          <button type="submit" className="rounded-xl bg-ink px-5 py-3 text-sm font-medium text-white hover:bg-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">Lưu thay đổi</button>
        </div>
      </form>
    </Dialog>
  );
}

// ---- V3 - 13. Xác nhận xóa dữ liệu ----
export function ConfirmClearDialog({ open, onClose, onConfirm, count }) {
  return (
    <Dialog open={open} onClose={onClose} labelledBy="xoa-title" width="max-w-[440px]">
      <div className="flex flex-col items-center text-center">
        <span className="grid size-14 place-items-center rounded-full bg-[#fdf1f0] text-[#c0443f]"><Icon name="trash" size={24} /></span>
        <h2 id="xoa-title" className="mt-4 text-lg font-medium">Xóa toàn bộ dữ liệu của bạn?</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          {count > 0 ? `${count} cuộc trò chuyện, ` : ""}thông tin đã nhập ở form và cài đặt trên trình duyệt này sẽ bị xóa. Thao tác này không thể hoàn tác.
        </p>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-2.5">
        <button onClick={onClose} className="rounded-xl border border-line py-3 text-sm font-medium hover:bg-soft focus-visible:outline-2 focus-visible:outline-brand">Hủy</button>
        <button onClick={onConfirm} className="rounded-xl bg-[#c0443f] py-3 text-sm font-medium text-white hover:bg-[#a5352f] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#c0443f]">Xóa dữ liệu</button>
      </div>
    </Dialog>
  );
}
