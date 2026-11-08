import { useEffect, useState } from "react";
import { DATA_UPDATED } from "../config.js";
import { getBanks } from "../lib/api.js";
import { DEFAULT_RATE, fmtDate, schedule, shortVnd, vnd } from "../lib/loan.js";
import { Icon, Orb } from "./icons.jsx";

const FEATURES = [
  ["chat", "Giải đáp thủ tục vay", "Hỏi bằng tiếng Việt về hồ sơ, điều kiện, quy trình 5 giai đoạn từ nộp hồ sơ đến giải ngân."],
  ["calc", "Ước tính trả hằng tháng", "Tính theo trả đều hoặc gốc đều, có lãi ưu đãi rồi thả nổi. Số liệu do máy chủ tính, không do AI tự đoán."],
  ["bars", "Xem gói vay ngân hàng", "Lãi ưu đãi, lãi sau ưu đãi, tỷ lệ cho vay và thời hạn tối đa của từng gói vay mẫu."],
  ["shield", "Rõ nguồn, rõ ngày", "Mỗi con số đều kèm ngày cập nhật. Thông tin chỉ để tham khảo, bạn xác nhận lại với ngân hàng."],
];

const STEPS = [
  ["Nhập thông tin", "Số tiền muốn vay, thời hạn, giá nhà và thu nhập. Không cần họ tên hay số CCCD."],
  ["Xem ước tính", "Tiền trả mỗi tháng, tổng lãi, tỷ lệ vay trên giá nhà và trả nợ trên thu nhập."],
  ["Hỏi trợ lý AI", "Hỏi tiếp về hồ sơ, ưu đãi, rủi ro lãi thả nổi để chuẩn bị trước khi gặp ngân hàng."],
];

// Ví dụ minh họa ở phần đầu trang, tính bằng cùng công thức với backend
const SAMPLE = (() => {
  const rows = schedule(1_500_000_000, 240, DEFAULT_RATE);
  return { monthly: rows[0].payment, interest: rows.reduce((t, r) => t + r.interest, 0) };
})();

const rateText = (r) => String(r).replace(".", ",") + "%";

function PrimaryButton({ onClick, children, className = "" }) {
  return (
    <button type="button" onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-xl bg-ink px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${className}`}>
      {children}
    </button>
  );
}

function SecondaryButton({ onClick, children, className = "" }) {
  return (
    <button type="button" onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-xl border border-line bg-white px-5 py-3 text-sm font-medium transition-colors hover:border-brand hover:text-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${className}`}>
      {children}
    </button>
  );
}

function ChatPreview() {
  return (
    <div className="relative">
      <div className="absolute -inset-4 -z-10 rounded-[32px] bg-white/40 blur-2xl" aria-hidden="true" />
      <div className="flex flex-col gap-4 rounded-[22px] border border-line bg-white p-5 shadow-[0_12px_40px_rgba(30,70,40,0.10)] sm:p-6" aria-label="Ví dụ một lượt hỏi đáp" role="img">
        <div className="flex items-center gap-2.5 border-b border-line pb-3.5">
          <Orb size={24} />
          <span className="text-sm font-medium">Trợ lý vay mua nhà</span>
          <span className="ml-auto rounded-full bg-mint px-2.5 py-1 text-[11px] text-muted">Ví dụ minh họa</span>
        </div>
        <p className="max-w-[85%] self-end rounded-[18px] bg-soft px-4 py-2.5 text-sm">Mình cần vay 1,5 tỷ trong 20 năm</p>
        <div className="flex gap-2.5">
          <div className="mt-0.5"><Orb size={22} /></div>
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <p className="text-sm leading-relaxed">Với khoản vay 1,5 tỷ đồng trong 20 năm, bạn có thể tham khảo ước tính bên dưới.</p>
            <div className="rounded-2xl border border-line p-4">
              <p className="text-xs text-muted">Ước tính trả hàng tháng</p>
              <p className="mt-1 text-[26px] font-light leading-none">{vnd(SAMPLE.monthly)}<span className="ml-1.5 text-sm text-muted">/ tháng</span></p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-mint px-3 py-2"><p className="text-[11px] text-muted">Thời hạn</p><p className="text-xs font-medium">20 năm</p></div>
                <div className="rounded-lg bg-mint px-3 py-2"><p className="text-[11px] text-muted">Tổng lãi dự kiến</p><p className="text-xs font-medium">{vnd(SAMPLE.interest)}</p></div>
              </div>
              <p className="mt-2.5 text-[11px] text-muted">Giả định lãi {rateText(DEFAULT_RATE)}/năm cố định, trả đều hằng tháng.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function BankCard({ bank }) {
  const ir = bank.interest_rate ?? {};
  const lim = bank.loan_limit ?? {};
  const rows = [
    ir.promo_rate != null && ["Lãi ưu đãi", `${rateText(ir.promo_rate)}/năm, ${ir.promo_duration_months} tháng đầu`],
    ir.floating_rate_estimated != null && ["Sau ưu đãi (ước tính)", `${rateText(ir.floating_rate_estimated)}/năm`],
    lim.max_ltv_percent != null && ["Cho vay tối đa", `${lim.max_ltv_percent}% giá trị nhà`],
    lim.max_loan_term_years != null && ["Thời hạn tối đa", `${lim.max_loan_term_years} năm`],
    lim.max_loan_amount != null && ["Hạn mức tối đa", shortVnd(lim.max_loan_amount)],
  ].filter(Boolean);
  return (
    <li className="flex flex-col gap-4 rounded-[18px] border border-line bg-white p-5">
      <div>
        <p className="text-base font-medium">{bank.short_name}</p>
        <p className="mt-0.5 text-xs leading-snug text-muted">{bank.package_name}</p>
      </div>
      <dl className="flex flex-col gap-2 text-[13px]">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-dashed border-line pb-2 last:border-0 last:pb-0">
            <dt className="text-muted">{k}</dt>
            <dd className="text-right font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-auto text-[11px] text-muted">Cập nhật {fmtDate(bank.last_updated)}</p>
    </li>
  );
}

export default function Home({ onChat, onForm }) {
  const [banks, setBanks] = useState(null);
  const [banksError, setBanksError] = useState(false);

  useEffect(() => {
    let alive = true;
    getBanks()
      .then((d) => alive && setBanks(d.banks))
      .catch(() => alive && setBanksError(true));
    return () => { alive = false; };
  }, []);

  const jump = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  const nav = [["tinh-nang", "Tính năng"], ["cach-dung", "Cách dùng"], ["ngan-hang", "Gói vay"]];

  return (
    <div className="h-dvh overflow-y-auto" style={{ background: "linear-gradient(160deg,#F3FAD6 0%,#E4F6EA 45%,#F7FBF4 100%)" }}>
      <header className="sticky top-0 z-10 border-b border-white/60 bg-[#f6fbef]/80 backdrop-blur">
        <div className="mx-auto flex max-w-[1120px] items-center gap-6 px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-2.5">
            <Orb size={28} />
            <span className="whitespace-nowrap text-[15px] font-medium">Trợ lý vay mua nhà</span>
          </div>
          <nav aria-label="Mục trên trang" className="hidden items-center gap-1 md:flex">
            {nav.map(([id, label]) => (
              <button key={id} type="button" onClick={() => jump(id)} className="rounded-lg px-3 py-2 text-sm text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-brand">{label}</button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden sm:contents"><SecondaryButton onClick={onForm} className="!py-2.5">Nhập thông tin vay</SecondaryButton></span>
            <PrimaryButton onClick={onChat} className="whitespace-nowrap !px-4 !py-2.5">Hỏi trợ lý AI</PrimaryButton>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-[1120px] items-center gap-12 px-4 pb-16 pt-10 sm:px-6 lg:grid-cols-[1.2fr_1fr] lg:pb-24 lg:pt-20">
          <div className="flex flex-col gap-6">
            <p className="flex w-fit items-center gap-2 rounded-full border border-line bg-white px-3.5 py-1.5 text-[13px] text-muted">
              <span className="size-1.5 rounded-full bg-[#4fc47a]" aria-hidden="true" />
              Dữ liệu cập nhật {fmtDate(DATA_UPDATED)}
            </p>
            <h1 className="text-[34px] font-medium leading-[1.15] text-balance sm:text-[44px] xl:text-[48px]">
              Hiểu rõ khoản vay mua nhà
              <span className="block text-brand">trước khi đến <span className="whitespace-nowrap">ngân hàng</span></span>
            </h1>
            <p className="max-w-[520px] text-[17px] leading-relaxed text-muted">
              Trợ lý AI giải đáp thủ tục, điều kiện vay và ước tính số tiền phải trả mỗi tháng theo lãi suất của các ngân hàng. Miễn phí, không cần đăng ký.
            </p>
            <div className="flex flex-wrap gap-3">
              <PrimaryButton onClick={onChat} className="px-6 py-3.5 text-[15px]">
                <Icon name="chat" size={18} strokeWidth={1.8} /> Hỏi trợ lý AI
              </PrimaryButton>
              <SecondaryButton onClick={onForm} className="px-6 py-3.5 text-[15px]">
                <Icon name="calc" size={18} strokeWidth={1.6} /> Nhập thông tin khoản vay
              </SecondaryButton>
            </div>
            <ul className="flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-muted">
              {["Không cần họ tên, số CCCD", "Không lưu lại dữ liệu bạn nhập", "Số liệu kèm ngày cập nhật"].map((t) => (
                <li key={t} className="flex items-center gap-1.5"><Icon name="check" size={15} strokeWidth={2} className="text-brand" />{t}</li>
              ))}
            </ul>
          </div>
          <ChatPreview />
        </section>

        <section id="tinh-nang" aria-labelledby="tinh-nang-title" className="scroll-mt-20 bg-white/70 py-16 lg:py-20">
          <div className="mx-auto max-w-[1120px] px-4 sm:px-6">
            <h2 id="tinh-nang-title" className="text-[26px] font-medium leading-tight sm:text-[32px]">Trợ lý giúp được gì?</h2>
            <p className="mt-2 max-w-[560px] text-pretty text-muted">Từ lúc mới tìm hiểu đến khi chuẩn bị hồ sơ, bạn có một chỗ để hỏi và tính thử.</p>
            <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map(([icon, title, desc]) => (
                <li key={title} className="flex flex-col gap-3 rounded-[18px] border border-line bg-white p-5">
                  <span className="grid size-10 place-items-center rounded-xl bg-mint text-brand"><Icon name={icon} size={20} strokeWidth={1.6} /></span>
                  <p className="font-medium">{title}</p>
                  <p className="text-sm leading-relaxed text-muted">{desc}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="cach-dung" aria-labelledby="cach-dung-title" className="mx-auto max-w-[1120px] scroll-mt-20 px-4 py-16 sm:px-6 lg:py-20">
          <h2 id="cach-dung-title" className="text-[26px] font-medium leading-tight sm:text-[32px]">Ba bước để có con số tham khảo</h2>
          <ol className="mt-8 grid gap-4 md:grid-cols-3">
            {STEPS.map(([title, desc], i) => (
              <li key={title} className="flex gap-4 rounded-[18px] border border-line bg-white p-5">
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-ink text-sm font-medium text-white">{i + 1}</span>
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{desc}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-8 flex flex-col gap-5 rounded-[22px] bg-ink p-6 text-white sm:flex-row sm:items-center sm:justify-between sm:p-8">
            <div>
              <p className="text-xl font-medium">Đã có số tiền và thời hạn muốn vay?</p>
              <p className="mt-1 text-sm text-white/70">Điền form để xem ngay tiền trả mỗi tháng, so với điều kiện của từng ngân hàng.</p>
            </div>
            <button type="button" onClick={onForm}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[#d8f37f] px-6 py-3.5 text-[15px] font-medium text-ink transition-colors hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
              Nhập thông tin khoản vay <Icon name="arrow" size={18} strokeWidth={2} />
            </button>
          </div>
        </section>

        <section id="ngan-hang" aria-labelledby="ngan-hang-title" className="scroll-mt-20 bg-white/70 py-16 lg:py-20">
          <div className="mx-auto max-w-[1120px] px-4 sm:px-6">
            <h2 id="ngan-hang-title" className="text-[26px] font-medium leading-tight sm:text-[32px]">Gói vay mua nhà tham khảo</h2>
            <p className="mt-2 max-w-[620px] text-pretty text-muted">Dữ liệu mẫu nhập tay từ website ngân hàng. Lãi suất thực tế phụ thuộc hồ sơ và thời điểm vay.</p>
            {banksError ? (
              <p className="mt-8 rounded-xl border border-line bg-white px-4 py-3 text-sm text-muted">Chưa tải được dữ liệu ngân hàng. Bạn vẫn có thể hỏi trợ lý hoặc tự nhập lãi suất trong form.</p>
            ) : banks === null ? (
              <p className="mt-8 text-sm text-muted" role="status">Đang tải dữ liệu ngân hàng...</p>
            ) : (
              <ul className="mt-8 grid gap-4 md:grid-cols-3">
                {banks.map((b) => <BankCard key={b.id} bank={b} />)}
              </ul>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              <PrimaryButton onClick={onForm}>Tính khoản vay với các gói này</PrimaryButton>
              <SecondaryButton onClick={onChat}>Hỏi trợ lý nên chọn gói nào</SecondaryButton>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1120px] flex-col gap-3 px-4 py-8 text-xs leading-relaxed text-muted sm:px-6">
          <div className="flex items-center gap-2 text-ink"><Orb size={20} /><span className="text-sm font-medium">Trợ lý vay mua nhà</span></div>
          <p>
            Thông tin chỉ mang tính tham khảo, vui lòng xác nhận trực tiếp với ngân hàng. Kết quả ước tính không phải cam kết cho vay.
            Nội dung quy trình tham khảo Thông tư 39/2016/TT-NHNN và website của Vietcombank, BIDV, Techcombank.
          </p>
          <p>Dự án sinh viên IUH. Dữ liệu cập nhật {fmtDate(DATA_UPDATED)}.</p>
        </div>
      </footer>
    </div>
  );
}
