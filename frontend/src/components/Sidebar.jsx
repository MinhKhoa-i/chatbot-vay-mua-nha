import { Icon, Orb } from "./icons.jsx";

export default function Sidebar({ convos, activeId, open, onClose, onNew, onSelect, onClear }) {
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-black/30 lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside
        className={`${open ? "flex" : "hidden"} fixed inset-y-3 left-3 z-30 w-[300px] max-w-[85vw] flex-col gap-5 rounded-[22px] bg-white p-5 shadow-xl lg:static lg:flex lg:shadow-none`}
        aria-label="Thanh bên"
      >
        <div className="flex items-center justify-between">
          <button onClick={onClose} aria-label="Đóng thanh bên" className="rounded-lg p-1 text-muted focus-visible:outline-2 focus-visible:outline-brand lg:invisible">
            <Icon name="close" size={18} />
          </button>
          <button onClick={onNew} aria-label="Cuộc trò chuyện mới" title="Cuộc trò chuyện mới"
            className="grid size-10 place-items-center rounded-full border border-line text-muted hover:bg-soft focus-visible:outline-2 focus-visible:outline-brand">
            <Icon name="edit" size={17} strokeWidth={1.5} />
          </button>
        </div>

        <div className="flex items-center gap-2.5 rounded-2xl border border-line px-3.5 py-3">
          <Orb size={22} />
          <span className="text-sm font-medium">Trợ lý vay mua nhà</span>
        </div>

        <nav aria-label="Lịch sử trò chuyện" className="min-h-0 flex-1 overflow-y-auto">
          {convos.length === 0 ? (
            <p className="px-2.5 text-[13px] leading-relaxed text-muted">Các cuộc trò chuyện của bạn sẽ hiện ở đây.</p>
          ) : (
            <ul className="flex flex-col gap-0.5">
              {convos.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => onSelect(c.id)}
                    aria-current={c.id === activeId ? "true" : undefined}
                    className={`w-full rounded-[10px] px-2.5 py-2.5 text-left text-[13px] leading-snug focus-visible:outline-2 focus-visible:outline-brand ${
                      c.id === activeId ? "bg-soft font-medium text-ink" : "text-muted hover:bg-soft"
                    }`}
                  >
                    {c.title}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>

        <button onClick={onClear} className="flex items-center gap-3 rounded-[10px] px-2.5 py-2 text-sm text-[#c0443f] hover:bg-soft focus-visible:outline-2 focus-visible:outline-brand">
          <Icon name="trash" size={16} strokeWidth={1.5} />
          Xóa dữ liệu của tôi
        </button>
      </aside>
    </>
  );
}
