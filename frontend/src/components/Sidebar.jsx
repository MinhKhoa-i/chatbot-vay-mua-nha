import { Icon, Orb } from "./icons.jsx";

const focus = "focus-visible:outline-2 focus-visible:outline-brand";
const itemCls = `flex w-full items-center gap-3 rounded-[10px] px-2.5 py-2.5 text-left text-sm max-lg:min-h-11 ${focus}`;

// Nút tròn của thanh bên thu gọn (V3 - 14), chú thích hiện khi rê chuột hoặc dùng bàn phím
function RailButton({ icon, label, onClick, danger, active }) {
  return (
    <button onClick={onClick} aria-label={label} aria-current={active ? "page" : undefined}
      className={`group relative grid size-11 place-items-center rounded-xl ${focus} ${danger ? "text-[#c0443f]" : "text-ink"} ${active ? "bg-soft" : "hover:bg-soft"}`}>
      <Icon name={icon} size={18} strokeWidth={1.6} />
      <span role="tooltip" className="pointer-events-none absolute left-full top-1/2 z-40 ml-3 -translate-y-1/2 whitespace-nowrap rounded-lg bg-ink px-2.5 py-1.5 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
        {label}
      </span>
    </button>
  );
}

export default function Sidebar({
  convos, activeId, open, onClose, onNew, onSelect, onClear, onHome,
  collapsed, onToggleCollapse, onHistory, onSettings,
}) {
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-black/30 lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside
        className={`${open ? "flex" : "hidden"} fixed inset-y-3 left-3 z-30 w-[300px] max-w-[85vw] flex-col rounded-[22px] bg-white shadow-xl lg:static lg:z-10 lg:flex lg:shadow-none ${collapsed ? "lg:w-[76px]" : ""}`}
        aria-label="Thanh bên"
      >
        {collapsed && (
          <div className="hidden h-full flex-col items-center gap-2 py-5 lg:flex">
            <RailButton icon="expand" label="Mở rộng thanh bên" onClick={onToggleCollapse} />
            <RailButton icon="edit" label="Cuộc trò chuyện mới" onClick={onNew} />
            <span className="my-1 grid size-11 place-items-center rounded-xl bg-soft" title="Trợ lý vay mua nhà"><Orb size={24} /></span>
            <RailButton icon="home" label="Trang chủ" onClick={onHome} />
            <div className="flex-1" />
            <RailButton icon="clock" label="Lịch sử trò chuyện" onClick={onHistory} />
            <RailButton icon="settings" label="Cài đặt" onClick={onSettings} />
            <RailButton icon="trash" label="Xóa dữ liệu của tôi" onClick={onClear} danger />
          </div>
        )}

        <div className={`h-full min-h-0 flex-col gap-5 p-5 ${collapsed ? "flex lg:hidden" : "flex"}`}>
          <div className="flex items-center justify-between">
            <button onClick={onClose} aria-label="Đóng thanh bên" className={`-ml-2.5 grid size-11 place-items-center rounded-lg text-muted lg:hidden ${focus}`}>
              <Icon name="close" size={18} />
            </button>
            <button onClick={onToggleCollapse} aria-label="Thu gọn thanh bên" title="Thu gọn thanh bên" className={`hidden rounded-lg p-1 text-muted hover:text-ink lg:block ${focus}`}>
              <Icon name="collapse" size={18} strokeWidth={1.6} />
            </button>
            <button onClick={onNew} aria-label="Cuộc trò chuyện mới" title="Cuộc trò chuyện mới"
              className={`grid size-11 place-items-center rounded-full border border-line text-muted hover:bg-soft lg:size-10 ${focus}`}>
              <Icon name="edit" size={17} strokeWidth={1.5} />
            </button>
          </div>

          <div className="flex items-center gap-2.5 rounded-2xl border border-line px-3.5 py-3">
            <Orb size={22} />
            <span className="text-sm font-medium">Trợ lý vay mua nhà</span>
          </div>

          <div className="-mt-2 flex flex-col">
            <button onClick={onHome} className={`${itemCls} text-muted hover:bg-soft hover:text-ink`}>
              <Icon name="home" size={16} strokeWidth={1.5} />
              Trang chủ
            </button>
          </div>

          <nav aria-label="Các cuộc trò chuyện gần đây" className="min-h-0 flex-1 overflow-y-auto">
            {convos.length === 0 ? (
              <p className="px-2.5 text-[13px] leading-relaxed text-muted">Các cuộc trò chuyện của bạn sẽ hiện ở đây.</p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {convos.map((c) => (
                  <li key={c.id}>
                    <button
                      onClick={() => onSelect(c.id)}
                      aria-current={c.id === activeId ? "true" : undefined}
                      className={`w-full rounded-[10px] px-2.5 py-2.5 text-left max-lg:min-h-11 text-[13px] leading-snug ${focus} ${
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

          <div className="flex flex-col gap-0.5">
            <button onClick={onHistory} className={`${itemCls} hover:bg-soft`}>
              <Icon name="clock" size={16} strokeWidth={1.6} />
              Lịch sử trò chuyện
            </button>
            <button onClick={onSettings} className={`${itemCls} hover:bg-soft`}>
              <Icon name="settings" size={16} strokeWidth={1.6} />
              Cài đặt
            </button>
            <button onClick={onClear} className={`${itemCls} text-[#c0443f] hover:bg-soft`}>
              <Icon name="trash" size={16} strokeWidth={1.5} />
              Xóa dữ liệu của tôi
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
