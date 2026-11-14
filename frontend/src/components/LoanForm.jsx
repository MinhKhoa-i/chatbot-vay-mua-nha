import { useEffect, useState } from "react";
import { ApiError, estimateLoan, getBanks } from "../lib/api.js";
import { DEFAULT_RATE, fmtDate, shortVnd, vnd } from "../lib/loan.js";
import { Icon } from "./icons.jsx";

// Giá trị form giữ dạng chuỗi như trong ô nhập; tiền chỉ giữ chữ số
export const EMPTY_LOAN_FORM = {
  propertyType: "", location: "", price: "", collateral: "",
  amount: "", years: "20", method: "annuity", bankId: "", rate: String(DEFAULT_RATE).replace(".", ","),
  income: "", debts: "",
};

const PROPERTY_TYPES = ["Căn hộ chung cư", "Nhà riêng, nhà đất", "Nhà dự án đang xây (hình thành trong tương lai)", "Đất nền"];
const COLLATERALS = ["Chính căn nhà mua", "Tài sản khác (nhà đất, sổ tiết kiệm...)", "Chưa rõ"];
const METHODS = [
  ["annuity", "Trả đều hằng tháng", "Gốc + lãi bằng nhau mỗi tháng (khi lãi không đổi)"],
  ["reducing_balance", "Gốc đều, lãi giảm dần", "Tháng đầu trả nhiều nhất, sau đó giảm dần"],
];
const DTI_REF = 50; // % tham khảo, xem ghi chú công thức trong backend/finance/calculator.py

const toInt = (s) => (s === "" ? null : Number(s));
const toRate = (s) => (s.trim() === "" ? NaN : Number(s.replace(",", ".")));
const pct = (x) => new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(x) + "%";

function validate(v, bank) {
  const e = {};
  const amount = toInt(v.amount);
  const price = toInt(v.price);
  const years = Number(v.years);
  if (!amount) e.amount = "Nhập số tiền muốn vay.";
  else if (amount < 1e6) e.amount = "Số tiền vay phải từ 1 triệu đồng trở lên.";
  if (!Number.isInteger(years) || years < 1 || years > 35) e.years = "Thời hạn vay từ 1 đến 35 năm.";
  if (price !== null && price < 1e6) e.price = "Giá trị nhà phải từ 1 triệu đồng trở lên.";
  if (amount && price && amount > price) e.amount = "Số tiền vay đang lớn hơn giá trị nhà.";
  if (!bank || bank.interest_rate.floating_rate_estimated == null) {
    const r = toRate(v.rate);
    if (!Number.isFinite(r) || r < 0 || r > 30) e.rate = "Lãi suất từ 0 đến 30%/năm, ví dụ 8,5.";
  }
  if (v.debts && !v.income) e.income = "Nhập thu nhập để tính tỷ lệ trả nợ trên thu nhập.";
  return e;
}

// So khoản vay với điều kiện của gói vay mẫu; chỉ để nhắc, không phải kết quả thẩm định
function checkNotes({ est, bank, price, income, debts }) {
  const out = [];
  const ltv = price ? (est.amount / price) * 100 : null;
  const dti = income ? ((est.monthly_payment + (debts ?? 0)) / income) * 100 : null;
  const limit = est.max_loan;
  if (limit && est.amount > limit.max_loan) {
    out.push(`Số tiền muốn vay ${shortVnd(est.amount)} lớn hơn hạn mức vay tối đa ước tính ${shortVnd(limit.max_loan)}.`);
  }
  if (dti !== null && dti > DTI_REF) out.push(`Tổng tiền trả nợ mỗi tháng bằng ${pct(dti)} thu nhập, cao hơn mức ${DTI_REF}% thường được xem là an toàn.`);
  if (!bank) return { ltv, dti, notes: out };
  const lim = bank.loan_limit ?? {};
  const name = bank.short_name;
  if (ltv !== null && lim.max_ltv_percent != null && ltv > lim.max_ltv_percent) out.push(`Khoản vay bằng ${pct(ltv)} giá trị nhà, vượt mức tối đa ${pct(lim.max_ltv_percent)} của ${name} (khi chỉ thế chấp chính căn nhà).`);
  if (lim.max_loan_amount != null && est.amount > lim.max_loan_amount) out.push(`Số tiền vay vượt hạn mức tối đa ${shortVnd(lim.max_loan_amount)} của ${name}.`);
  if (lim.min_loan_amount != null && est.amount < lim.min_loan_amount) out.push(`Số tiền vay thấp hơn mức tối thiểu ${shortVnd(lim.min_loan_amount)} của ${name}.`);
  if (lim.max_loan_term_years != null && est.years > lim.max_loan_term_years) out.push(`Thời hạn vượt mức tối đa ${lim.max_loan_term_years} năm của ${name}.`);
  if (lim.min_loan_term_years != null && est.years < lim.min_loan_term_years) out.push(`Thời hạn ngắn hơn mức tối thiểu ${lim.min_loan_term_years} năm của ${name}.`);
  const minIncome = bank.eligibility?.min_monthly_income;
  if (income && minIncome != null && income < minIncome) out.push(`Thu nhập thấp hơn mức tối thiểu ${shortVnd(minIncome)}/tháng mà ${name} yêu cầu.`);
  if (bank.repayment_methods && !bank.repayment_methods.includes(est.method)) out.push(`${name} chưa ghi nhận phương thức trả nợ này trong dữ liệu mẫu.`);
  return { ltv, dti, notes: out };
}

function Field({ id, label, hint, error, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">{label}</label>
      {children}
      {error ? (
        <p id={`${id}-err`} className="text-xs text-[#c0443f]">{error}</p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

const inputCls = (err) =>
  `h-11 w-full rounded-xl border bg-white px-3.5 text-[15px] outline-none focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/20 ${err ? "border-[#c0443f]" : "border-line"}`;

function MoneyInput({ id, value, onChange, error, placeholder }) {
  const shown = value === "" ? "" : new Intl.NumberFormat("vi-VN").format(Number(value));
  return (
    <div className="relative">
      <input
        id={id} inputMode="numeric" autoComplete="off" value={shown} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 15))}
        aria-invalid={!!error} aria-describedby={error ? `${id}-err` : `${id}-hint`}
        className={`${inputCls(error)} pr-10`}
      />
      <span className="pointer-events-none absolute inset-y-0 right-3.5 grid place-items-center text-sm text-muted">đ</span>
    </div>
  );
}

function Section({ title, note, children }) {
  return (
    <fieldset className="flex flex-col gap-4 rounded-[18px] border border-line bg-white p-5 sm:p-6">
      <legend className="sr-only">{title}</legend>
      <div>
        <h2 className="text-[15px] font-medium" aria-hidden="true">{title}</h2>
        {note && <p className="mt-0.5 text-xs text-muted">{note}</p>}
      </div>
      {children}
    </fieldset>
  );
}

function MaxLoan({ est, bank, hasInputs }) {
  const limit = est.max_loan;
  if (!limit) {
    if (hasInputs || est.max_loan === undefined) return null;
    return <p className="text-[13px] text-muted">Nhập cả giá trị nhà và thu nhập để xem hạn mức vay tối đa.</p>;
  }
  const ltvSource = bank?.loan_limit?.max_ltv_percent != null ? `theo ${bank.short_name}` : "mức tham khảo";
  const rows = [
    [`Theo giá trị nhà (cho vay tối đa ${pct(limit.max_ltv_percent)}, ${ltvSource})`, limit.by_ltv, "ltv"],
    [`Theo thu nhập (trả nợ tối đa ${pct(limit.max_dti_percent)} thu nhập)`, limit.by_dti, "dti"],
  ];
  const within = est.amount <= limit.max_loan;
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line px-4 py-3.5">
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
        <p className="text-sm font-medium">Hạn mức vay tối đa ước tính</p>
        <p className="whitespace-nowrap text-xl font-medium">{vnd(limit.max_loan)}</p>
      </div>
      <dl className="flex flex-col gap-1.5 text-[13px]">
        {rows.map(([label, value, key]) => (
          <div key={key} className="flex justify-between gap-3">
            <dt className={limit.limited_by === key ? "font-medium" : "text-muted"}>
              {label}{limit.limited_by === key && " · đang giới hạn"}
            </dt>
            <dd className="whitespace-nowrap text-right font-medium">{vnd(value)}</dd>
          </div>
        ))}
      </dl>
      <p className={`text-[13px] ${within ? "text-brand" : "text-[#9a5b00]"}`}>
        {within ? "Số tiền muốn vay nằm trong hạn mức ước tính." : "Số tiền muốn vay đang vượt hạn mức ước tính."}
      </p>
      <p className="text-xs leading-relaxed text-muted">
        Tính theo tháng phải trả cao nhất trong kỳ hạn. Đây là ước tính theo tỷ lệ tham khảo, không phải hạn mức ngân hàng phê duyệt.
      </p>
    </div>
  );
}

function Result({ result, onAsk }) {
  const { est, bank } = result;
  const { ltv, dti, notes } = checkNotes(result);
  const promo = est.promo_rate != null && est.promo_duration_months > 0;
  const stats = [
    ["Số tiền vay", vnd(est.amount)],
    ["Thời hạn", `${est.years} năm`],
    ["Tổng lãi dự kiến", vnd(est.total_interest)],
    ["Tổng phải trả", vnd(est.amount + est.total_interest)],
  ];
  if (ltv !== null) stats.push(["Tỷ lệ vay / giá trị nhà", pct(ltv)]);
  if (dti !== null) stats.push(["Trả nợ / thu nhập", pct(dti)]);
  const rateText = (r) => String(r).replace(".", ",") + "%/năm";

  return (
    <section aria-labelledby="loan-result" className="flex flex-col gap-4 rounded-[18px] border border-line bg-white p-5 sm:p-6">
      <h2 id="loan-result" className="text-[13px] text-muted">
        {est.method === "reducing_balance" ? "Ước tính trả tháng đầu (cao nhất)" : promo ? "Ước tính trả hàng tháng trong thời gian ưu đãi" : "Ước tính trả hàng tháng"}
      </h2>
      <p className="flex flex-wrap items-end gap-x-2.5">
        <span className="text-[34px] font-light leading-none sm:text-[44px]">{vnd(est.monthly_payment)}</span>
        <span className="text-base text-muted">/ tháng</span>
      </p>
      <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        {stats.map(([k, v]) => (
          <div key={k} className="rounded-xl bg-mint px-3.5 py-3">
            <dt className="text-xs text-muted">{k}</dt>
            <dd className="mt-0.5 text-sm font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      <MaxLoan est={est} bank={bank} hasInputs={Boolean(result.price && result.income)} />
      {notes.length > 0 && (
        <div className="rounded-xl border border-[#f0d9a8] bg-[#fdf7ea] px-4 py-3">
          <p className="text-sm font-medium">Cần lưu ý</p>
          <ul className="mt-1.5 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-relaxed">
            {notes.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </div>
      )}
      <p className="text-xs leading-relaxed text-muted">
        {promo
          ? `Giả định lãi ưu đãi ${rateText(est.promo_rate)} trong ${est.promo_duration_months} tháng đầu, sau đó ${rateText(est.rate)} đến hết kỳ hạn; khi hết ưu đãi số tiền trả hằng tháng sẽ thay đổi. `
          : `Giả định lãi suất ${rateText(est.rate)} cố định cả kỳ hạn. `}
        {bank
          ? `Lãi suất lấy từ dữ liệu mẫu của ${bank.short_name}, cập nhật ${fmtDate(bank.last_updated)}. ${bank.disclaimer}`
          : "Đây là ví dụ minh họa, chưa phải lãi suất của một ngân hàng cụ thể."}
        {" "}Dữ liệu tính toán cập nhật {fmtDate(est.updated_at)}. Vui lòng xác nhận trực tiếp với ngân hàng.
      </p>
      <div>
        <button type="button" onClick={onAsk} className="rounded-xl bg-ink px-5 py-3 text-sm font-medium text-white hover:bg-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">
          Hỏi trợ lý về khoản vay này
        </button>
      </div>
    </section>
  );
}

export default function LoanForm({ values: v, onChange, onBack, onAsk }) {
  const [banks, setBanks] = useState(null);
  const [banksError, setBanksError] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let alive = true;
    getBanks()
      .then((d) => alive && setBanks(d.banks))
      .catch(() => alive && setBanksError(true));
    return () => { alive = false; };
  }, []);

  const bank = banks?.find((b) => b.id === v.bankId) ?? null;
  const ir = bank?.interest_rate;
  const needRate = !bank || ir.floating_rate_estimated == null;
  const bankPromo = Boolean(bank && ir.promo_rate != null && ir.promo_duration_months > 0);
  const set = (k) => (val) => {
    onChange({ ...v, [k]: val });
    if (errors[k]) setErrors((e) => ({ ...e, [k]: undefined }));
  };
  const setFromEvent = (k) => (e) => set(k)(e.target.value);

  async function submit(e) {
    e.preventDefault();
    const errs = validate(v, bank);
    setErrors(errs);
    setSubmitError("");
    const first = Object.keys(errs).find((k) => errs[k]);
    if (first) { document.getElementById(`f-${first}`)?.focus(); return; }

    const params = { amount: Number(v.amount), years: Number(v.years), method: v.method };
    if (bankPromo) {
      params.promo_rate = ir.promo_rate;
      params.promo_duration_months = ir.promo_duration_months;
    }
    params.rate = needRate ? toRate(v.rate) : ir.floating_rate_estimated;
    if (toInt(v.price) && toInt(v.income)) {
      params.property_value = toInt(v.price);
      params.monthly_income = toInt(v.income);
      params.existing_monthly_debt = toInt(v.debts) ?? 0;
      params.max_dti_percent = DTI_REF;
      if (bank?.loan_limit?.max_ltv_percent != null) params.max_ltv_percent = bank.loan_limit.max_ltv_percent;
    }

    setBusy(true);
    try {
      const est = await estimateLoan(params);
      setResult({ est, bank, price: toInt(v.price), income: toInt(v.income), debts: toInt(v.debts),
        propertyType: v.propertyType, location: v.location.trim(), collateral: v.collateral });
    } catch (err) {
      setResult(null);
      setSubmitError(err instanceof ApiError ? err.message : "Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy và địa chỉ API trong file .env, rồi thử lại.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    onChange(EMPTY_LOAN_FORM);
    setErrors({});
    setSubmitError("");
    setResult(null);
  }

  function ask() {
    const { est } = result;
    const parts = [`Mình muốn vay ${shortVnd(est.amount)} trong ${est.years} năm`];
    if (result.bank) parts.push(`ở ${result.bank.short_name}`);
    const home = [result.propertyType ? result.propertyType.toLowerCase() : "nhà", result.location && `ở ${result.location}`,
      result.price && `giá khoảng ${shortVnd(result.price)}`].filter(Boolean).join(" ");
    parts.push(`để mua ${home}`);
    let text = parts.join(" ");
    if (result.collateral) text += `. Tài sản bảo đảm: ${result.collateral.toLowerCase()}`;
    onAsk(text + ". Bạn tư vấn giúp mình nhé.");
  }

  const priceN = toInt(v.price);
  const amountN = toInt(v.amount);
  const ltvHint = priceN && amountN && amountN <= priceN ? `Bằng ${pct((amountN / priceN) * 100)} giá trị nhà.` : "";

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
      <div className="mx-auto flex max-w-[740px] flex-col gap-5">
        <div className="flex flex-col gap-2">
          <button type="button" onClick={onBack} className="-ml-1 flex w-fit items-center gap-1.5 rounded-lg px-1 py-1 text-sm text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-brand">
            <Icon name="arrow" size={16} className="rotate-180" /> Quay lại trò chuyện
          </button>
          <h1 className="text-[26px] font-medium leading-tight sm:text-[32px]">Thông tin khoản vay</h1>
          <p className="text-sm leading-relaxed text-muted">
            Nhập vài thông tin để ước tính số tiền trả hằng tháng. Chỉ cần số tiền vay và thời hạn, các mục khác có thể bỏ trống.
            Thông tin chỉ dùng để tính trên trang này, không lưu lại. Không cần nhập họ tên, số CCCD hay số tài khoản.
          </p>
        </div>

        <form onSubmit={submit} noValidate className="flex flex-col gap-5">
          <Section title="Căn nhà dự định mua" note="Không bắt buộc. Giá trị nhà dùng để tính tỷ lệ cho vay và hạn mức vay tối đa.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="f-propertyType" label="Loại nhà">
                <select id="f-propertyType" value={v.propertyType} onChange={setFromEvent("propertyType")} className={inputCls()}>
                  <option value="">Chọn loại nhà</option>
                  {PROPERTY_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </Field>
              <Field id="f-location" label="Khu vực" hint="Tỉnh/thành, không cần địa chỉ cụ thể.">
                <input id="f-location" value={v.location} onChange={setFromEvent("location")} maxLength={60} placeholder="Ví dụ: TP. Hồ Chí Minh" aria-describedby="f-location-hint" className={inputCls()} />
              </Field>
              <Field id="f-price" label="Giá trị nhà" hint={priceN ? `Khoảng ${shortVnd(priceN)}.` : "Giá mua hoặc giá trị ước tính."} error={errors.price}>
                <MoneyInput id="f-price" value={v.price} onChange={set("price")} error={errors.price} placeholder="Ví dụ: 2.500.000.000" />
              </Field>
              <Field id="f-collateral" label="Tài sản bảo đảm">
                <select id="f-collateral" value={v.collateral} onChange={setFromEvent("collateral")} className={inputCls()}>
                  <option value="">Chọn tài sản bảo đảm</option>
                  {COLLATERALS.map((t) => <option key={t}>{t}</option>)}
                </select>
              </Field>
            </div>
          </Section>

          <Section title="Khoản vay">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="f-amount" label="Số tiền muốn vay *" hint={[amountN ? `Khoảng ${shortVnd(amountN)}.` : "", ltvHint].join(" ").trim()} error={errors.amount}>
                <MoneyInput id="f-amount" value={v.amount} onChange={set("amount")} error={errors.amount} placeholder="Ví dụ: 1.500.000.000" />
              </Field>
              <Field id="f-years" label="Thời hạn vay (năm) *" hint="Từ 1 đến 35 năm." error={errors.years}>
                <input id="f-years" type="number" inputMode="numeric" min={1} max={35} step={1} value={v.years} onChange={setFromEvent("years")}
                  aria-invalid={!!errors.years} aria-describedby={errors.years ? "f-years-err" : "f-years-hint"} className={inputCls(errors.years)} />
              </Field>
            </div>

            <div role="radiogroup" aria-label="Phương thức trả nợ" className="grid gap-2.5 sm:grid-cols-2">
              {METHODS.map(([val, title, desc]) => (
                <label key={val} className={`flex cursor-pointer gap-3 rounded-xl border p-3.5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-brand ${v.method === val ? "border-brand bg-mint" : "border-line"}`}>
                  <input type="radio" name="method" value={val} checked={v.method === val} onChange={() => set("method")(val)} className="mt-0.5 accent-[#1e6b58]" />
                  <span>
                    <span className="block text-sm font-medium">{title}</span>
                    <span className="block text-xs text-muted">{desc}</span>
                  </span>
                </label>
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="f-bankId" label="Ngân hàng" hint={banksError ? "Không tải được danh sách ngân hàng, bạn có thể tự nhập lãi suất." : banks === null ? "Đang tải danh sách ngân hàng..." : "Lấy lãi suất từ dữ liệu mẫu, hoặc tự nhập."}>
                <select id="f-bankId" value={v.bankId} onChange={setFromEvent("bankId")} disabled={!banks} aria-describedby="f-bankId-hint" className={`${inputCls()} disabled:bg-soft`}>
                  <option value="">Không chọn, tự nhập lãi suất</option>
                  {banks?.map((b) => <option key={b.id} value={b.id}>{b.short_name}</option>)}
                </select>
              </Field>
              {needRate && (
                <Field id="f-rate" label={bankPromo ? "Lãi suất sau ưu đãi (%/năm) *" : "Lãi suất (%/năm) *"}
                  hint={bankPromo ? "Ví dụ 9,5. Áp dụng từ khi hết ưu đãi đến hết kỳ hạn." : "Ví dụ 8,5. Áp dụng cố định cả kỳ hạn."} error={errors.rate}>
                  <input id="f-rate" inputMode="decimal" value={v.rate} onChange={(e) => set("rate")(e.target.value.replace(/[^\d.,]/g, "").slice(0, 6))}
                    aria-invalid={!!errors.rate} aria-describedby={errors.rate ? "f-rate-err" : "f-rate-hint"} className={inputCls(errors.rate)} />
                </Field>
              )}
            </div>

            {bank && (
              <div className="rounded-xl bg-soft px-4 py-3 text-[13px] leading-relaxed">
                <p className="font-medium">{bank.short_name}: {bank.package_name}</p>
                <p className="text-muted">
                  {ir.promo_rate != null && `Ưu đãi ${String(ir.promo_rate).replace(".", ",")}%/năm trong ${ir.promo_duration_months} tháng đầu. `}
                  {ir.floating_rate_estimated != null && `Sau ưu đãi ước tính ${String(ir.floating_rate_estimated).replace(".", ",")}%/năm (lãi tham chiếu + biên độ ${String(ir.floating_margin).replace(".", ",")}%). `}
                  {bank.loan_limit?.max_ltv_percent != null && `Cho vay tối đa ${bank.loan_limit.max_ltv_percent}% giá trị nhà, thời hạn tối đa ${bank.loan_limit.max_loan_term_years} năm. `}
                  Cập nhật {fmtDate(bank.last_updated)}.
                </p>
              </div>
            )}
          </Section>

          <Section title="Thu nhập và nghĩa vụ trả nợ" note="Không bắt buộc. Dùng để tính tỷ lệ trả nợ trên thu nhập và hạn mức vay tối đa.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="f-income" label="Thu nhập ròng mỗi tháng" hint="Sau thuế, có thể gồm thu nhập người cùng trả nợ." error={errors.income}>
                <MoneyInput id="f-income" value={v.income} onChange={set("income")} error={errors.income} placeholder="Ví dụ: 40.000.000" />
              </Field>
              <Field id="f-debts" label="Đang trả nợ khác mỗi tháng" hint="Tổng tiền trả góp, vay khác hằng tháng.">
                <MoneyInput id="f-debts" value={v.debts} onChange={set("debts")} placeholder="Ví dụ: 5.000.000" />
              </Field>
            </div>
          </Section>

          {submitError && <p role="alert" className="rounded-xl border border-[#f1c7c4] bg-[#fdf1f0] px-4 py-3 text-sm text-[#c0443f]">{submitError}</p>}

          <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
            <button type="submit" disabled={busy} className="rounded-xl bg-ink px-6 py-3 text-sm font-medium text-white hover:bg-brand disabled:bg-[#9a9c98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">
              {busy ? "Đang tính..." : "Tính khoản vay"}
            </button>
            <button type="button" onClick={reset} className="text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand">
              Nhập lại
            </button>
          </div>
        </form>

        <div aria-live="polite">{result && <Result result={result} onAsk={ask} />}</div>
      </div>
    </div>
  );
}
