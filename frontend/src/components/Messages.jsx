import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import { ApiError, estimateLoan } from "../lib/api.js";
import { DEFAULT_RATE, fmtDate, vnd } from "../lib/loan.js";
import { Icon, Orb } from "./icons.jsx";

const hasNumbers = (e) => e.monthly_payment != null && e.total_interest != null;

// Số trên thẻ luôn do backend tính (POST /api/estimate -> calculator.py).
// Câu trả lời chat đã kèm số thì dùng luôn, thiếu thì gọi /api/estimate.
function useServerEstimate(estimate) {
  const [state, setState] = useState(() => (hasNumbers(estimate) ? { est: estimate } : { loading: true }));
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (hasNumbers(estimate)) return;
    let alive = true;
    setState({ loading: true });
    estimateLoan({
      amount: Math.round(estimate.amount),
      years: estimate.years,
      rate: estimate.rate ?? DEFAULT_RATE,
      method: estimate.method ?? "annuity",
      promo_rate: estimate.promo_rate ?? null,
      promo_duration_months: estimate.promo_duration_months ?? 0,
    })
      .then((est) => alive && setState({ est }))
      .catch((err) => alive && setState({
        error: err instanceof ApiError ? err.message : "Không kết nối được máy chủ để tính khoản vay. Hãy kiểm tra backend đang chạy rồi thử lại.",
      }));
    return () => { alive = false; };
  }, [estimate, attempt]);
  return { ...state, retry: () => setAttempt((n) => n + 1) };
}

function EstimateCard({ estimate, onCompare, onAdjust }) {
  const { est, loading, error, retry } = useServerEstimate(estimate);
  const shell = "flex flex-col gap-4 rounded-[18px] border border-line bg-white p-5 sm:p-6";
  if (loading) {
    return <p className={`${shell} text-sm text-muted`} role="status">Đang tính khoản vay...</p>;
  }
  if (error) {
    return (
      <div className={shell} role="alert">
        <p className="text-sm text-[#c0443f]">{error}</p>
        <button onClick={retry} className="w-fit text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand">Thử lại</button>
      </div>
    );
  }
  const rate = (r) => String(r).replace(".", ",") + "%/năm";
  const promo = est.promo_rate != null && est.promo_duration_months > 0;
  const stats = [
    ["Số tiền vay", vnd(est.amount)],
    ["Thời hạn", `${est.years} năm`],
    ["Tổng lãi dự kiến", vnd(est.total_interest)],
  ];
  return (
    <div className={shell}>
      <p className="text-[13px] text-muted">{est.method === "reducing_balance" ? "Ước tính trả tháng đầu (cao nhất)" : "Ước tính trả hàng tháng"}</p>
      <p className="flex flex-wrap items-end gap-x-2.5">
        <span className="text-[34px] font-light leading-none sm:text-[44px]">{vnd(est.monthly_payment)}</span>
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
        {promo
          ? `Giả định lãi ưu đãi ${rate(est.promo_rate)} trong ${est.promo_duration_months} tháng đầu, sau đó ${rate(est.rate)}`
          : `Giả định lãi suất ${rate(est.rate)} cố định`},{" "}
        {est.method === "reducing_balance" ? "trả gốc đều, lãi giảm dần" : "trả đều gốc và lãi hằng tháng"}.
        Đây là ví dụ minh họa, chưa phải lãi suất của một ngân hàng cụ thể.
        {est.updated_at && ` Dữ liệu cập nhật ${fmtDate(est.updated_at)}.`}
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

// Câu trả lời của bot viết bằng Markdown (**đậm**, danh sách "- ", link nguồn).
// react-markdown không chạy HTML thô trong câu trả lời, nên hiển thị an toàn.
const MD = {
  p: (props) => <p className="my-0 [&:not(:first-child)]:mt-3" {...props} />,
  strong: (props) => <strong className="font-semibold" {...props} />,
  ul: (props) => <ul className="mt-2 list-disc space-y-1.5 pl-6 first:mt-0" {...props} />,
  ol: (props) => <ol className="mt-2 list-decimal space-y-1.5 pl-6 first:mt-0" {...props} />,
  li: (props) => <li className="pl-1" {...props} />,
  h1: (props) => <h3 className="mt-4 font-semibold first:mt-0" {...props} />,
  h2: (props) => <h3 className="mt-4 font-semibold first:mt-0" {...props} />,
  h3: (props) => <h3 className="mt-4 font-semibold first:mt-0" {...props} />,
  a: ({ node, ...props }) => (
    <a className="break-words text-brand underline underline-offset-2" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  table: (props) => <div className="mt-3 overflow-x-auto"><table className="w-full border-collapse text-[15px]" {...props} /></div>,
  th: (props) => <th className="border border-line bg-soft px-3 py-1.5 text-left font-semibold" {...props} />,
  td: (props) => <td className="border border-line px-3 py-1.5" {...props} />,
};

function BotText({ text }) {
  return (
    <div className="text-[length:var(--chat-fs,17px)] leading-[1.6]">
      <Markdown remarkPlugins={[remarkGfm, remarkBreaks]} components={MD}>{text}</Markdown>
    </div>
  );
}

// V3 - 9. Lỗi kết nối: câu hỏi chưa được trả lời, cho thử lại hoặc sao chép câu hỏi
const ERROR_INFO = {
  NETWORK_ERROR: ["Không kết nối được máy chủ", "Câu hỏi của bạn chưa được xử lý. Hãy kiểm tra kết nối mạng và máy chủ đang chạy rồi thử lại."],
  server: ["Máy chủ chưa trả lời được", "Dịch vụ trợ lý đang lỗi hoặc quá tải nên câu hỏi chưa được trả lời. Bạn thử lại sau ít phút nhé."],
};
export const errorInfo = (code) => ERROR_INFO[code] ?? ERROR_INFO.server;

function ErrorCard({ m, canRetry, onRetry }) {
  const [copied, setCopied] = useState(false);
  const [title, text] = errorInfo(m.code);
  const copy = async () => {
    try { await navigator.clipboard.writeText(m.question ?? ""); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* trình duyệt chặn clipboard */ }
  };
  return (
    <div role="alert" className="flex gap-4 rounded-[20px] border border-[#f1c9c6] bg-[#fdf1f0] p-5 sm:p-6">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-[#c0443f]"><Icon name="wifiOff" size={18} /></span>
      <div className="min-w-0 flex-1">
        <p className="font-medium">{title}</p>
        <p className="mt-1 text-sm leading-relaxed">{text}</p>
        <p className="mt-1.5 text-xs text-muted">Mã lỗi: {m.code ?? "UNKNOWN"}{m.time ? ` · ${m.time}` : ""}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
          {canRetry && (
            <button onClick={onRetry} className="flex items-center gap-2 rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-white hover:bg-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">
              <Icon name="redo" size={15} /> Thử lại
            </button>
          )}
          {m.question && (
            <button onClick={copy} className="text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand">
              {copied ? "Đã sao chép" : "Sao chép câu hỏi"}
            </button>
          )}
        </div>
      </div>
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
            <p key={m.id} className="max-w-[85%] self-end whitespace-pre-line rounded-[20px] bg-soft px-5 py-3.5 text-[length:calc(var(--chat-fs,17px)-1px)] leading-relaxed sm:max-w-[75%]">{m.text}</p>
          ) : (
            <div key={m.id} className="flex gap-3.5">
              <div className="mt-0.5"><Orb size={28} /></div>
              <div className="flex min-w-0 flex-1 flex-col gap-5">
                {m.error
                  ? <ErrorCard m={m} canRetry={i === last && !loading} onRetry={onRegenerate} />
                  : <BotText text={m.text} />}
                {m.estimate && (
                  <EstimateCard estimate={m.estimate} onCompare={() => onAsk("So sánh lãi suất ngân hàng")} onAdjust={() => onAdjust(m.estimate)} />
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
