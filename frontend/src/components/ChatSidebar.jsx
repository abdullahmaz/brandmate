import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  PlusIcon,
  MessageSquare,
  PanelLeftClose,
  PanelLeft,
  Loader2,
  Trash2,
  Sun,
  Moon,
  Search,
  Gem,
} from 'lucide-react';
import { useChats, useDeleteChat } from '../hooks/useChat';
import { useTheme } from './ThemeProvider';
import { cn } from '../lib/utils';
import { isToday, isYesterday, isThisWeek, isThisMonth } from 'date-fns';

function groupChats(chats) {
  const groups = { Today: [], Yesterday: [], 'This week': [], 'This month': [], Older: [] };
  for (const c of chats) {
    const d = new Date(c.updated_at || c.created_at);
    if (isToday(d)) groups['Today'].push(c);
    else if (isYesterday(d)) groups['Yesterday'].push(c);
    else if (isThisWeek(d)) groups['This week'].push(c);
    else if (isThisMonth(d)) groups['This month'].push(c);
    else groups['Older'].push(c);
  }
  return Object.entries(groups).filter(([, items]) => items.length > 0);
}

export function ChatSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const { data: chats, isLoading } = useChats();
  const deleteChatMutation = useDeleteChat();
  const [deletingId, setDeletingId] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState('');

  const activeChatId = location.pathname.split('/chat/')[1] ?? null;
  const filtered = (chats || []).filter((c) =>
    !search.trim() || (c.title || '').toLowerCase().includes(search.toLowerCase())
  );
  const grouped = search.trim() ? null : groupChats(filtered);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    setDeletingId(id);
    try {
      await deleteChatMutation.mutateAsync(id);
      if (activeChatId === id) navigate('/chat');
    } catch {}
    finally { setDeletingId(null); }
  };

  return (
    /* Outer shell transitions its width */
    <div
      className="relative flex-shrink-0 bg-sidebar border-r border-sidebar-border h-full overflow-hidden transition-[width] duration-300 ease-in-out"
      style={{ width: collapsed ? '56px' : '260px' }}
    >
      {/* ── EXPANDED content ─────────────────────────────────── */}
      <div className={cn(
        'absolute inset-0 flex flex-col transition-[opacity,transform] duration-300 ease-in-out',
        collapsed ? 'opacity-0 -translate-x-3 pointer-events-none' : 'opacity-100 translate-x-0'
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-3 pt-3 pb-2 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <Gem className="h-3.5 w-3.5 text-primary flex-shrink-0" />
            <span className="font-brand text-base font-semibold text-sidebar-foreground select-none tracking-wide">
              Brandmate
            </span>
          </div>
          <div className="flex items-center gap-0.5">
            <IconBtn onClick={toggleTheme} title="Toggle theme" sm>
              {theme === 'light' ? <Moon className="h-[14px] w-[14px]" /> : <Sun className="h-[14px] w-[14px]" />}
            </IconBtn>
            <IconBtn onClick={() => setCollapsed(true)} title="Collapse" sm>
              <PanelLeftClose className="h-[14px] w-[14px]" />
            </IconBtn>
          </div>
        </div>

        {/* New chat */}
        <div className="px-2 pb-1 flex-shrink-0">
          <button
            onClick={() => navigate('/chat')}
            className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
          >
            <PlusIcon className="h-4 w-4 flex-shrink-0" />
            <span>New chat</span>
          </button>
        </div>

        {/* Search */}
        <div className="px-2 pb-2 flex-shrink-0">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-sidebar-foreground/50" />
            <input
              type="text"
              placeholder="Search…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-sidebar-border pl-8 pr-3 py-1.5 text-xs text-sidebar-foreground outline-none focus:border-ring/50 transition-colors"
              style={{ background: 'var(--sidebar-accent)', color: 'var(--sidebar-foreground)' }}
            />
          </div>
        </div>

        {/* Chat list */}
        <div className="sidebar-scroll flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
          <div className="w-full px-2 pb-3">
            {isLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-4 w-4 animate-spin text-sidebar-foreground/40" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-10 text-sidebar-foreground/40">
                <MessageSquare className="h-6 w-6" />
                <p className="text-xs">{search ? 'No matches' : 'No chats yet'}</p>
              </div>
            ) : search.trim() ? (
              filtered.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  active={activeChatId === chat.id}
                  deleting={deletingId === chat.id}
                  onSelect={() => navigate(`/chat/${chat.id}`)}
                  onDelete={(e) => handleDelete(e, chat.id)}
                />
              ))
            ) : (
              grouped.map(([label, items]) => (
                <div key={label} className="mb-1">
                  <p className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/35 select-none">
                    {label}
                  </p>
                  {items.map((chat) => (
                    <ChatItem
                      key={chat.id}
                      chat={chat}
                      active={activeChatId === chat.id}
                      deleting={deletingId === chat.id}
                      onSelect={() => navigate(`/chat/${chat.id}`)}
                      onDelete={(e) => handleDelete(e, chat.id)}
                    />
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── COLLAPSED icon strip ──────────────────────────────── */}
      <div className={cn(
        'absolute inset-0 flex flex-col items-center py-3 gap-1 transition-[opacity,transform] duration-300 ease-in-out',
        collapsed ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-3 pointer-events-none'
      )}>
        <IconBtn onClick={() => setCollapsed(false)} title="Expand">
          <PanelLeft className="h-[18px] w-[18px]" />
        </IconBtn>
        <IconBtn onClick={() => navigate('/chat')} title="New chat">
          <PlusIcon className="h-[18px] w-[18px]" />
        </IconBtn>
        <div className="flex-1" />
        <IconBtn onClick={toggleTheme} title="Toggle theme">
          {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </IconBtn>
      </div>
    </div>
  );
}

/* ── ChatItem ─────────────────────────────────────────────────── */
function ChatItem({ chat, active, deleting, onSelect, onDelete }) {
  return (
    <div
      className={cn(
        'group relative flex w-full min-w-0 items-center overflow-hidden rounded-lg cursor-pointer mb-0.5',
        active ? 'text-sidebar-foreground' : 'text-sidebar-foreground/70'
      )}
      style={{ background: active ? 'var(--sidebar-accent)' : undefined }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--sidebar-accent)'; e.currentTarget.style.color = 'var(--sidebar-foreground)'; }}
      onMouseLeave={e => { if (!active) { e.currentTarget.style.background = ''; e.currentTarget.style.color = ''; } }}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect()}
    >
      <span className="block min-w-0 flex-1 truncate py-2 pl-3 pr-8 text-sm">
        {chat.title || 'Untitled'}
      </span>
      <button
        onClick={onDelete}
        disabled={deleting}
        tabIndex={-1}
        title="Delete"
        className={cn(
          'absolute right-1.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md transition-colors',
          'opacity-0 group-hover:opacity-100 text-sidebar-foreground/50 hover:text-destructive hover:bg-destructive/10',
          deleting && 'opacity-100 text-sidebar-foreground/50'
        )}
      >
        {deleting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
      </button>
    </div>
  );
}

/* ── IconBtn ──────────────────────────────────────────────────── */
function IconBtn({ children, onClick, title, sm = false }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={cn(
        'flex items-center justify-center rounded-lg text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors',
        sm ? 'h-7 w-7' : 'h-9 w-9'
      )}
    >
      {children}
    </button>
  );
}
