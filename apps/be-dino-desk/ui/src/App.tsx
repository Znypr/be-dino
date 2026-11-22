// Be Dino Desk (docs/247): tabs of groups of pictures; Like / Dislike / Upgrade + a note per item, a note per group.
// Every change saves the whole feedback file (debounced) through main.js -> docs/feedback/asset-desk.json.
// The last tab, Menus (BD-1301, views/Menus.tsx), compares each menu proposal with its build per element; notes -> menu-feedback.json.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, FolderOpen, RefreshCw, Sparkles, ThumbsDown, ThumbsUp, Bone } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Kbd } from '@/components/ui/kbd';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { desk, now, query, type Catalog, type Feedback, type Group, type Item, type Verdict } from './desk';
import Specimens, { SPECIMENS } from './views/Specimens';
import Menus from './views/Menus';
import { runSmoke } from './smoke';

export type Filter = 'all' | 'unrated' | Verdict;
type Bg = 'dark' | 'green' | 'light';
type Size = 's' | 'm' | 'l';
const SIZES: Record<Size, number> = { s: 120, m: 180, l: 260 };
const BGS: Record<Bg, string> = { dark: '#202024', green: '#79c76a', light: '#e9e9ee' };
export const VERDICTS: { v: Verdict; label: string; key: string; Icon: typeof ThumbsUp; cls: string }[] = [
  { v: 'like', label: 'Like', key: '1', Icon: ThumbsUp, cls: 'text-ok border-ok' },
  { v: 'dislike', label: 'Dislike', key: '2', Icon: ThumbsDown, cls: 'text-cut border-cut' },
  { v: 'upgrade', label: 'Upgrade', key: '3', Icon: Sparkles, cls: 'text-change border-change' },
];
const ring = (v?: Verdict) => (v === 'like' ? 'ring-2 ring-ok' : v === 'dislike' ? 'ring-2 ring-cut' : v === 'upgrade' ? 'ring-2 ring-change' : '');

export function useFeedback() {
  const [fb, setFb] = useState<Feedback>({ items: {}, groups: {} });
  const [state, setState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const timer = useRef<number>(0);
  useEffect(() => { desk.feedback.load().then((f) => setFb({ items: f.items || {}, groups: f.groups || {} })); }, []);
  const persist = useCallback((next: Feedback) => {
    setFb(next); setState('saving');
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      desk.feedback.save(next).then(() => setState('saved')).catch((e) => toast('Could not save: ' + String(e)));
    }, 350);
  }, []);
  const setItem = useCallback((id: string, patch: { verdict?: Verdict | null; note?: string }) => {
    setFb((cur) => {
      const old = cur.items[id] || {};
      const verdict = patch.verdict === null ? undefined : patch.verdict ?? old.verdict;
      const note = patch.note ?? old.note;
      const items = { ...cur.items };
      if (!verdict && !note) delete items[id]; else items[id] = { ...(verdict ? { verdict } : {}), ...(note ? { note } : {}), at: now() };
      const next = { ...cur, items };
      persist(next);
      return next;
    });
  }, [persist]);
  const setGroup = useCallback((id: string, note: string) => {
    setFb((cur) => {
      const groups = { ...cur.groups };
      if (note.trim()) groups[id] = { note, at: now() }; else delete groups[id];
      const next = { ...cur, groups };
      persist(next);
      return next;
    });
  }, [persist]);
  return { fb, setItem, setGroup, state };
}

function Tile({ item, size, bg, verdict, onOpen, onVerdict }: {
  item: Item; size: number; bg: string; verdict?: Verdict; onOpen: () => void; onVerdict: (v: Verdict) => void;
}) {
  return (
    <div className="group/tile flex flex-col gap-1" style={{ width: size }} data-item={item.id}>
      <button onClick={onOpen} className={cn('relative overflow-hidden rounded-md border', ring(verdict))} style={{ width: size, height: size, background: bg }}>
        <img src={desk.media(item.src)} alt={item.title} loading="lazy" draggable={false} className="size-full object-contain p-1.5" />
        <span className="absolute inset-x-1 bottom-1 flex justify-center gap-1 opacity-0 transition-opacity group-hover/tile:opacity-100">
          {VERDICTS.map(({ v, Icon, label }) => (
            <span key={v} role="button" title={label} onClick={(e) => { e.stopPropagation(); onVerdict(v); }}
              className={cn('flex size-7 items-center justify-center rounded-md border bg-background/90 text-muted-foreground hover:text-foreground',
                verdict === v && VERDICTS.find((x) => x.v === v)!.cls)}>
              <Icon className="size-3.5" />
            </span>
          ))}
        </span>
      </button>
      <span className="truncate text-xs text-muted-foreground" title={item.id}>{item.title}</span>
    </div>
  );
}

function GroupNote({ id, value, onSave }: { id: string; value: string; onSave: (id: string, note: string) => void }) {
  const [open, setOpen] = useState(!!value);
  const [text, setText] = useState(value);
  useEffect(() => setText(value), [value]);
  if (!open) return <button className="self-start text-xs text-muted-foreground hover:text-foreground" onClick={() => setOpen(true)}>Add a note on this group</button>;
  return <Textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} onBlur={() => onSave(id, text)}
    placeholder="What you think of this group as a whole (saved when you click away)" className="max-w-3xl text-sm" />;
}

export default function App() {
  const [cat, setCat] = useState<Catalog | null>(null);
  const [tab, setTab] = useState(0);
  const [filter, setFilter] = useState<Filter>('all');
  const [bg, setBg] = useState<Bg>('dark');
  const [size, setSize] = useState<Size>('m');
  const [open, setOpen] = useState<{ group: Group; index: number } | null>(null);
  const { fb, setItem, setGroup, state } = useFeedback();
  const scroller = useRef<HTMLDivElement>(null);

  const load = useCallback(() => desk.catalog().then(setCat).catch((e) => toast('Catalog failed: ' + String(e))), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (cat && query.get('smoke')) runSmoke(cat, { setTab, setFilter, setOpen, setItem }); }, [cat]);

  const menusTab = cat?.menus ? cat.tabs.length : -1;
  const onMenus = tab === menusTab;
  const groups = onMenus ? [] : cat?.tabs[tab]?.groups || [];
  const pass = useCallback((it: Item) => {
    const v = fb.items[it.id]?.verdict;
    return filter === 'all' || (filter === 'unrated' ? !v : v === filter);
  }, [fb, filter]);
  const counts = useMemo(() => {
    const c = { like: 0, dislike: 0, upgrade: 0 } as Record<Verdict, number>;
    for (const v of Object.values(fb.items)) if (v.verdict) c[v.verdict] += 1;
    return c;
  }, [fb]);

  const cur = open ? open.group.items[open.index] : null;
  const move = (d: number) => setOpen((o) => (o ? { ...o, index: (o.index + d + o.group.items.length) % o.group.items.length } : o));
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (!open || t.tagName === 'TEXTAREA' || t.tagName === 'INPUT') return;
      if (e.key === 'ArrowRight') { move(1); e.preventDefault(); }
      if (e.key === 'ArrowLeft') { move(-1); e.preventDefault(); }
      const v = VERDICTS.find((x) => x.key === e.key);
      if (v && cur) { setItem(cur.id, { verdict: fb.items[cur.id]?.verdict === v.v ? null : v.v }); e.preventDefault(); }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [open, cur, fb]);

  const isSpec = (g: Group) => g.kind === 'specimens';
  return (
    <div className="grid h-full grid-rows-[40px_1fr_28px]">
      <header className="flex items-center gap-3 border-b px-2">
        <span className="flex h-7 shrink-0 items-center gap-2 px-2 text-sm font-semibold"><Bone className="size-4 text-muted-foreground" />Be Dino Desk</span>
        <nav className="flex h-full" aria-label="Tabs">
          {[...(cat?.tabs || []), ...(cat?.menus ? [{ name: 'Menus' }] : [])].map((t, i) => (
            <button key={t.name} onClick={() => { setTab(i); scroller.current?.scrollTo({ top: 0 }); }}
              className={cn('relative flex h-full items-center px-3 text-sm text-muted-foreground hover:text-foreground',
                i === tab && 'text-foreground after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:bg-foreground')}>
              {t.name}
            </button>
          ))}
        </nav>
        <div className={cn('ml-auto flex items-center gap-2', onMenus && 'hidden')}>
          <ToggleGroup type="single" size="sm" variant="outline" value={filter} onValueChange={(v) => v && setFilter(v as Filter)}>
            {(['all', 'unrated', 'like', 'dislike', 'upgrade'] as Filter[]).map((f) => (
              <ToggleGroupItem key={f} value={f} className="px-2 text-xs capitalize">{f}</ToggleGroupItem>
            ))}
          </ToggleGroup>
          <ToggleGroup type="single" size="sm" variant="outline" value={bg} onValueChange={(v) => v && setBg(v as Bg)} title="Tile background">
            {(Object.keys(BGS) as Bg[]).map((b) => <ToggleGroupItem key={b} value={b} className="px-2 text-xs capitalize">{b}</ToggleGroupItem>)}
          </ToggleGroup>
          <ToggleGroup type="single" size="sm" variant="outline" value={size} onValueChange={(v) => v && setSize(v as Size)} title="Tile size">
            {(Object.keys(SIZES) as Size[]).map((s) => <ToggleGroupItem key={s} value={s} className="px-2 text-xs uppercase">{s}</ToggleGroupItem>)}
          </ToggleGroup>
          <Button variant="ghost" size="icon-sm" title="Reload the catalog" onClick={load}><RefreshCw /></Button>
        </div>
      </header>

      {onMenus && cat?.menus ? <Menus menus={cat.menus} /> : (
      <div className="grid min-h-0 grid-cols-[200px_1fr]">
        <aside className="min-h-0 overflow-y-auto border-r py-2">
          {groups.map((g) => {
            const rated = g.items.filter((it) => fb.items[it.id]?.verdict).length;
            const n = isSpec(g) ? SPECIMENS.length : g.items.length;
            return (
              <button key={g.id} onClick={() => document.getElementById('g-' + g.id)?.scrollIntoView({ block: 'start' })}
                className="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm hover:bg-accent">
                <span className="truncate">{g.name}</span>
                <span className="shrink-0 text-[11px] text-muted-foreground">{isSpec(g) ? n : `${rated}/${n}`}</span>
              </button>
            );
          })}
        </aside>
        <main ref={scroller} className="min-h-0 overflow-y-auto px-5 py-4">
          {!cat && <p className="text-sm text-muted-foreground">Loading the catalog...</p>}
          {groups.map((g) => (
            <section key={g.id} id={'g-' + g.id} className="mb-8 flex flex-col gap-2">
              <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{g.name}</h2>
              {g.note && <p className="max-w-4xl text-xs text-muted-foreground">{g.note}</p>}
              <GroupNote id={g.id} value={fb.groups[g.id]?.note || ''} onSave={setGroup} />
              {isSpec(g) ? <Specimens fb={fb} setItem={setItem} filter={filter} />
                : (
                  <div className="flex flex-wrap gap-3 pt-1">
                    {g.items.map((it, i) => pass(it) && (
                      <Tile key={it.id} item={it} size={SIZES[size]} bg={BGS[bg]} verdict={fb.items[it.id]?.verdict}
                        onOpen={() => setOpen({ group: g, index: i })}
                        onVerdict={(v) => setItem(it.id, { verdict: fb.items[it.id]?.verdict === v ? null : v })} />
                    ))}
                  </div>
                )}
            </section>
          ))}
        </main>
      </div>
      )}

      <footer className="flex items-center justify-between gap-3 border-t px-3 text-[11px] text-muted-foreground">
        {onMenus ? (
          <>
            <span className="flex items-center gap-3">
              <span>click a box: element · elsewhere or <Kbd className="h-4 border bg-transparent px-1 text-[10px]">Shift</Kbd>+click: pin</span>
              <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">1</Kbd>-<Kbd className="h-4 border bg-transparent px-1 text-[10px]">9</Kbd> tags</span>
              <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">Enter</Kbd> save</span>
              <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">Esc</Kbd> close</span>
              <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">B</Kbd> blink</span>
              <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">P</Kbd> pin mode</span>
              <span>wheel zoom · drag pan · <Kbd className="h-4 border bg-transparent px-1 text-[10px]">F</Kbd> fit</span>
            </span>
            <span>notes save to docs/feedback/menu-feedback.json</span>
          </>
        ) : (<>
        <span className="flex items-center gap-3">
          <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">1</Kbd> like</span>
          <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">2</Kbd> dislike</span>
          <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">3</Kbd> upgrade</span>
          <span><Kbd className="h-4 border bg-transparent px-1 text-[10px]">Left</Kbd><Kbd className="ml-0.5 h-4 border bg-transparent px-1 text-[10px]">Right</Kbd> next picture</span>
        </span>
        <span>{counts.like} liked · {counts.dislike} disliked · {counts.upgrade} to upgrade · {state === 'saving' ? 'saving...' : 'saved to docs/feedback/asset-desk.json'}</span>
        </>)}
      </footer>

      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        {cur && open && (
          <DialogContent className="sm:max-w-5xl">
            <DialogHeader>
              <DialogTitle className="text-sm">{cur.title}</DialogTitle>
              <DialogDescription className="truncate text-xs">{open.group.name} · {open.index + 1} of {open.group.items.length} · {cur.id}</DialogDescription>
            </DialogHeader>
            <div className="relative flex items-center justify-center rounded-md border" style={{ background: BGS[bg], height: '62vh' }}>
              <img src={desk.media(cur.src)} alt={cur.title} className="max-h-full max-w-full object-contain p-3" />
              <Button variant="ghost" size="icon-sm" className="absolute left-2" onClick={() => move(-1)}><ChevronLeft /></Button>
              <Button variant="ghost" size="icon-sm" className="absolute right-2" onClick={() => move(1)}><ChevronRight /></Button>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex gap-1.5">
                {VERDICTS.map(({ v, label, key, Icon, cls }) => (
                  <Button key={v} variant="outline" size="sm" className={cn(fb.items[cur.id]?.verdict === v && cls)}
                    onClick={() => setItem(cur.id, { verdict: fb.items[cur.id]?.verdict === v ? null : v })}>
                    <Icon />{label}<Kbd className="h-4 bg-transparent px-1 text-[10px]">{key}</Kbd>
                  </Button>
                ))}
              </div>
              <Textarea key={cur.id} rows={2} defaultValue={fb.items[cur.id]?.note || ''} className="flex-1 text-sm"
                placeholder="What exactly do you like or want changed? (saved when you click away)"
                onBlur={(e) => setItem(cur.id, { note: e.target.value.trim() })} />
              <Button variant="ghost" size="icon-sm" title="Show in folder" onClick={() => desk.openFile(cur.id)}><FolderOpen /></Button>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
