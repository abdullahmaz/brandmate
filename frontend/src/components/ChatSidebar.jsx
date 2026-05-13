import { useState, useEffect, useRef } from 'react';
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
  LogOut,
  LogIn,
} from 'lucide-react';
import { useChats, useDeleteChat } from '../hooks/useChat';
import { useTheme } from './ThemeProvider';
import { useAuth } from '../providers/AuthProvider';
import { cn } from '../lib/utils';
import { isToday, isYesterday, isThisWeek, isThisMonth } from 'date-fns';
import { BrandMark } from './BrandMark';

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
  const { session, user, signOut, openLoginDialog } = useAuth();

  const { data: chats, isLoading } = useChats();
  const deleteChatMutation = useDeleteChat();
  const [deletingId, setDeletingId] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e) => {
      if (!menuRef.current?.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [menuOpen]);

  const initial = (user?.email?.[0] || '?').toUpperCase();
  const displayName = user?.user_metadata?.full_name || user?.email || 'Signed in';

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
    <div
      className="relative flex-shrink-0 bg-sidebar border-r border-sidebar-border h-full overflow-hidden transition-[width] duration-300 ease-in-out"
      style={{ width: collapsed ? '60px' : '272px' }}
    >
      {/* ── EXPANDED content ─────────────────────────────────── */}
      <div className={cn(
        'absolute inset-0 flex flex-col transition-[opacity,transform] duration-300 ease-in-out',
        collapsed ? 'opacity-0 -translate-x-3 pointer-events-none' : 'opacity-100 translate-x-0'
      )}>
        {/* Masthead */}
        <div className="px-4 pt-4 pb-3 flex-shrink-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <BrandMark size={26} tone="duo" />
              <div className="flex flex-col leading-none min-w-0">
                <span className="font-brand text-[22px] font-semibold text-sidebar-foreground tracking-tight select-none">
                  Brandmate
                </span>
                <span className="font-brand-italic text-[11px] text-sidebar-foreground/55 mt-0.5 select-none truncate">
                  the eastern atelier, in pixels
                </span>
              </div>
            </div>
            <div className="flex items-center gap-0.5 flex-shrink-0 pt-1">
              <IconBtn onClick={toggleTheme} title="Toggle theme" sm>
                {theme === 'light' ? <Moon className="h-[14px] w-[14px]" /> : <Sun className="h-[14px] w-[14px]" />}
              </IconBtn>
              <IconBtn onClick={() => setCollapsed(true)} title="Collapse" sm>
                <PanelLeftClose className="h-[14px] w-[14px]" />
              </IconBtn>
            </div>
          </div>
          <hr className="rule-double mt-3" />
        </div>

        {/* New chat */}
        <div className="px-2 pb-1 flex-shrink-0">
          <button
            onClick={() => navigate('/chat')}
            className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground/85 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors border border-transparent hover:border-sidebar-border"
          >
            <PlusIcon className="h-4 w-4 flex-shrink-0" />
            <span>New brief</span>
          </button>
        </div>

        {/* Search */}
        <div className="px-2 pb-3 flex-shrink-0">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-sidebar-foreground/50" />
            <input
              type="text"
              placeholder="Search the archive…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-md border border-sidebar-border pl-8 pr-3 py-1.5 text-xs text-sidebar-foreground outline-none focus:border-ring/60 transition-colors"
              style={{ background: 'var(--card)', color: 'var(--foreground)' }}
            />
          </div>
        </div>

        {/* Chat list */}
        <div className="sidebar-scroll flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
          <div className="w-full px-2 pb-3">
            {!session ? (
              <div className="flex flex-col items-center gap-2 py-12 px-4 text-center text-sidebar-foreground/55">
                <BrandMark size={28} tone="accent" />
                <p className="font-brand-italic text-xs leading-snug">
                  Sign in to see your saved briefs.
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-4 w-4 animate-spin text-sidebar-foreground/40" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-12 text-sidebar-foreground/50">
                <BrandMark size={28} tone="accent" />
                <p className="font-brand-italic text-xs">{search ? 'Nothing matches' : 'No briefs yet'}</p>
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
                <div key={label} className="mb-2">
                  <p className="flourish-dot px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-sidebar-foreground/45 select-none font-brand">
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

        {/* Footer: user menu when signed in, sign-in CTA when not */}
        <div ref={menuRef} className="relative flex-shrink-0 px-2 py-2 border-t border-sidebar-border/60">
          {session ? (
            <>
              {menuOpen && (
                <div
                  className="absolute bottom-full left-2 right-2 mb-2 rounded-md border border-sidebar-border bg-sidebar shadow-lg overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={async () => { setMenuOpen(false); try { await signOut(); } catch {} }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-hover transition-colors"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Sign out</span>
                  </button>
                </div>
              )}
              <button
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                className="w-full flex items-center gap-2.5 rounded-md px-2 py-1.5 hover:bg-sidebar-hover transition-colors"
                title={user?.email || ''}
              >
                <span
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-[12px] font-brand font-semibold"
                  style={{
                    background: 'color-mix(in srgb, var(--accent) 25%, var(--sidebar-accent))',
                    color: 'var(--mark)',
                    border: '1px solid color-mix(in srgb, var(--accent) 40%, var(--sidebar-border))',
                  }}
                >
                  {initial}
                </span>
                <span className="min-w-0 flex-1 truncate text-left text-[13px] text-sidebar-foreground/85">
                  {displayName}
                </span>
              </button>
            </>
          ) : (
            <div className="flex flex-col gap-1.5">
              <button
                type="button"
                onClick={() => openLoginDialog('signin')}
                className="send-btn h-8 w-full rounded-md flex items-center justify-center gap-1.5 text-[13px]"
              >
                <LogIn className="h-3.5 w-3.5" />
                <span>Sign in</span>
              </button>
              <button
                type="button"
                onClick={() => openLoginDialog('signup')}
                className="h-7 w-full rounded-md text-[12px] font-brand-italic text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-hover transition-colors"
              >
                or create an account
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── COLLAPSED icon strip ──────────────────────────────── */}
      <div className={cn(
        'absolute inset-0 flex flex-col items-center py-3 gap-1 transition-[opacity,transform] duration-300 ease-in-out',
        collapsed ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-3 pointer-events-none'
      )}>
        <div className="pb-1.5">
          <BrandMark size={22} tone="duo" />
        </div>
        <IconBtn onClick={() => setCollapsed(false)} title="Expand">
          <PanelLeft className="h-[18px] w-[18px]" />
        </IconBtn>
        <IconBtn onClick={() => navigate('/chat')} title="New brief">
          <PlusIcon className="h-[18px] w-[18px]" />
        </IconBtn>
        <div className="flex-1" />
        <IconBtn onClick={toggleTheme} title="Toggle theme">
          {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </IconBtn>
        {!session && (
          <IconBtn onClick={() => openLoginDialog('signin')} title="Sign in">
            <LogIn className="h-4 w-4" />
          </IconBtn>
        )}
      </div>
    </div>
  );
}

/* ── ChatItem ─────────────────────────────────────────────────── */
function ChatItem({ chat, active, deleting, onSelect, onDelete }) {
  return (
    <div
      className={cn(
        'group relative flex w-full min-w-0 items-center overflow-hidden rounded-md cursor-pointer mb-0.5',
        active ? 'text-sidebar-foreground' : 'text-sidebar-foreground/75'
      )}
      style={{ background: active ? 'var(--sidebar-accent)' : undefined }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--sidebar-hover)'; e.currentTarget.style.color = 'var(--sidebar-foreground)'; }}
      onMouseLeave={e => { if (!active) { e.currentTarget.style.background = ''; e.currentTarget.style.color = ''; } }}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect()}
    >
      {active && (
        <span
          className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[2px] rounded-full"
          style={{ background: 'var(--primary)' }}
        />
      )}
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
        'flex items-center justify-center rounded-md text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors',
        sm ? 'h-7 w-7' : 'h-9 w-9'
      )}
    >
      {children}
    </button>
  );
}
