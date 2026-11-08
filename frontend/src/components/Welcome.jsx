import { SUGGESTIONS } from "../config.js";
import { Icon, Orb } from "./icons.jsx";

export default function Welcome({ onPick, onForm, children }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-6 sm:px-8">
      <div className="flex w-full max-w-[740px] flex-col gap-9">
        <div className="flex flex-col gap-5">
          <Orb size={64} glow />
          <h1 className="text-[32px] font-medium leading-[1.18] sm:text-[46px]">
            Xin chào,
            <span className="block text-faint">Bạn cần hỗ trợ gì hôm nay?</span>
          </h1>
        </div>
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {SUGGESTIONS.map((s) => (
            <li key={s.text}>
              <button onClick={() => (s.form ? onForm() : onPick(s.text))}
                className="flex h-[120px] w-full flex-col justify-between rounded-2xl border border-line bg-white p-4 text-left shadow-[0_3px_10px_rgba(20,30,20,0.05)] transition-colors hover:border-brand focus-visible:outline-2 focus-visible:outline-brand">
                <Icon name={s.icon} size={18} strokeWidth={1.5} className="text-faint" />
                <span className="text-[13px] font-medium leading-snug">{s.text}</span>
              </button>
            </li>
          ))}
        </ul>
        {children}
      </div>
    </div>
  );
}
