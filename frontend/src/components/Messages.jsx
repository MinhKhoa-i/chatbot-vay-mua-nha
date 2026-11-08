import { useEffect, useRef, useState } from "react";
import { annuity, DEFAULT_RATE, vnd } from "../lib/loan.js";
import { Icon, Orb } from "./icons.jsx";

function EstimateCard({ estimate, onCompare, onAdjust }) {
  const rate = estimate.rate ?? DEFAULT_RATE;
  // Ưu tiên số do backend tính (calculator.py); chỉ tự tính khi chạy mock hoặc server chưa gửi
  const local = estimate.monthly_payment == null ? annuity(estimate.amount, estimate.years, rate) : null;
  const monthly = estimate.monthly_payment ?? local.monthly;
  const interest = estimate.total_interest ?? local.interest;
  const stats = [
    ["Số tiền vay", vnd(estimate.amount)],
    ["Thời hạn", `${estimate.years} năm`],
    ["Tổng lãi dự kiến", vnd(interest)],
  ];
  return (
    <div className="flex flex-col gap-4 rounded-[18px] border border-line bg-white p-5 sm:p-6">
      <p className="text-[13px] text-muted">Ước tính trả hàng tháng</p>
      <p className="flex flex-wrap items-end gap-x-2.5">
        <span className="text-[34px] font-light leading-none sm:text-[44px]">{vnd(monthly)}</span>
        <span className="text-base text-muted">/ tháng</span>
      </p>
      <dl className="grid gap-2.5 sm:grid-cols-3">
        {stats.map(([k, v]) => (
          <div key={k} className="rounded-xl bg-mint px-3.5 py-3">
            <dt className="text-xs text-muted">{k}</dt>
            <dd className="mt-0.5 text-sm font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs leading-relaxed text-muted">
        Giả định lãi suất {String(rate).replace(".", ",")}%/năm cố định,{" "}
        {estimate.method === "reducing_balance" ? "trả gốc đều, lãi giảm dần (số trên là tháng đầu, cao nhất)" : "trả đều gốc và lãi hằng tháng"}.
        Đây là ví dụ minh họa, chưa phải lãi suất của một ngân hàng cụ thể.
      </p>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
        <button onClick={onCompare} className="rounded-xl bg-ink px-5 py-3 text-sm font-medium text-white hover:bg-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">
          So sánh ngân hàng phù hợp
        </button>
        <button onClick={onAdjust} className="text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand">
          Điều chỉnh thông tin
        </button>
      </div>
    </div>
  );
}

function Tools({ text, rating, onRate, onRegenerate }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* trình duyệt chặn clipboard */ }
  };
  const btn = "grid size-9 place-items-center rounded-lg text-muted hover:bg-soft hover:text-ink focus-visible:outline-2 focus-visible:outline-brand";
  return (
    <div className="-ml-2 flex items-center gap-1">
      <button onClick={copy} aria-label={copied ? "Đã sao chép" : "Sao chép câu trả lời"} title="Sao chép" className={btn}>
        <Icon name={copied ? "check" : "copy"} size={17} strokeWidth={1.6} />
      </button>
      <button onClick={() => onRate("up")} aria-pressed={rating === "up"} aria-label="Hữu ích" title="Hữu ích" className={`${btn} ${rating === "up" ? "bg-soft !text-brand" : ""}`}>
        <Icon name="up" size={17} strokeWidth={1.6} />
      </button>
      <button onClick={() => onRate("down")} aria-pressed={rating === "down"} aria-label="Không hữu ích" title="Không hữu ích" className={`${btn} ${rating === "down" ? "bg-soft !text-[#c0443f]" : ""}`}>
        <Icon name="down" size={17} strokeWidth={1.6} />
      </button>
      <button onClick={onRegenerate} aria-label="Tạo lại câu trả lời" title="Tạo lại câu trả lời" className={btn}>
        <Icon name="redo" size={17} strokeWidth={1.6} />
      </button>
    </div>
  );
}

function Typing() {
  return (
    <div className="flex items-center gap-3.5" role="status">
      <Orb size={28} />
      <span className="flex gap-1.5" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <i key={i} className="typing-dot size-[7px] rounded-full bg-muted" style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </span>
      <span className="text-base text-muted">Đang tìm kiếm thông tin...</span>
    </div>
  );
}

export default function Messages({ messages, loading, onRate, onRegenerate, onAsk, onAdjust }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [messages.length, loading]);
  const last = messages.length - 1;

  return (
    <div role="log" aria-live="polite" aria-label="Cuộc trò chuyện" className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
      <div className="mx-auto flex max-w-[740px] flex-col gap-8">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <p key={m.id} className="max-w-[85%] self-end whitespace-pre-line rounded-[20px] bg-soft px-5 py-3.5 leading-relaxed sm:max-w-[75%]">{m.text}</p>
          ) : (
            <div key={m.id} className="flex gap-3.5">
              <div className="mt-0.5"><Orb size={28} /></div>
              <div className="flex min-w-0 flex-1 flex-col gap-5">
                <p className={`whitespace-pre-line text-[17px] leading-[1.6] ${m.error ? "text-[#c0443f]" : ""}`}>{m.text}</p>
                {m.estimate && (
                  <EstimateCard estimate={m.estimate} onCompare={() => onAsk("So sánh lãi suất ngân hàng")} onAdjust={onAdjust} />
                )}
                {i === last && !loading && !m.error && (
                  <Tools text={m.text} rating={m.rating} onRate={(v) => onRate(m.id, v)} onRegenerate={onRegenerate} />
                )}
              </div>
            </div>
          )
        )}
        {loading && <Typing />}
        <div ref={endRef} />
      </div>
    </div>
  );
}
