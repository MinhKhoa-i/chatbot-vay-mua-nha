import { useEffect, useRef } from "react";
import { FEATURES } from "../config.js";
import { Icon } from "./icons.jsx";

export default function Composer({ value, onChange, onSend, disabled }) {
  const ref = useRef(null);
  const canSend = value.trim().length > 0 && !disabled;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 140) + "px";
  }, [value]);

  const submit = () => canSend && onSend();

  return (
    <div className="mx-auto w-full max-w-[740px]">
      <div className="rounded-[20px] p-[1.5px] shadow-[0_6px_22px_rgba(184,235,102,0.3)]"
        style={{ background: "linear-gradient(90deg,#C6EC7A,#7FD3F0)" }}>
        <div className="flex items-end gap-3 rounded-[18.5px] bg-white p-2.5 pl-3">
          {FEATURES.attach && (
            <button type="button" aria-label="Đính kèm tài liệu" className="grid size-11 shrink-0 place-items-center rounded-full bg-soft focus-visible:outline-2 focus-visible:outline-brand">
              <Icon name="plus" size={20} strokeWidth={1.8} />
            </button>
          )}
          <label htmlFor="msg" className="sr-only">Câu hỏi của bạn</label>
          <textarea
            id="msg" ref={ref} rows={1} maxLength={1000} value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Nhập câu hỏi của bạn"
            className="min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 text-base leading-snug outline-none placeholder:text-muted"
          />
          <button type="button" onClick={submit} disabled={!canSend} aria-label="Gửi"
            className="grid size-12 shrink-0 place-items-center rounded-full bg-ink text-white transition-colors enabled:hover:bg-brand disabled:bg-[#d9d9d6] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">
            <Icon name="arrow" size={20} strokeWidth={2} />
          </button>
        </div>
      </div>
      <p className="mt-3 px-2 text-center text-xs leading-relaxed text-muted">
        Thông tin chỉ mang tính tham khảo, vui lòng xác nhận trực tiếp với ngân hàng. Không nhập số CCCD, số tài khoản hay mật khẩu vào khung chat.
      </p>
    </div>
  );
}
