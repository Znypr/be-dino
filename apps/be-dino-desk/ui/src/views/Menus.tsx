// Menus tab (BD-1301, docs/247): the owner's PROPOSAL next to the BUILD for every docs/menu-specs/<screen>, every spec element drawn
// as a box (green = within tolerance, red = miss, grey = not built / not checked), with onion, blink (key B) and wipe to spot small
// differences. Click an element (on either picture or in the list) for its two crops, the measured numbers and the owner's note
// form (tags 1-9, note, must fix / nice to have, "should be"); click anywhere else (or Shift-click, or pin mode P) for a free pin.
// Every change is one operation on docs/feedback/menu-feedback.json (main.js; never written in smoke mode), which
// tools/menu_spec_check.py reads: an open must-fix note keeps that element failing.
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from 'react';
import { Check, MapPin, RotateCcw, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Kbd } from '@/components/ui/kbd';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { desk, type Box, type MenuFeedback, type MenuNote, type MenuOp, type MenuOpResult, type MenuPin, type MenuRow,
  type MenuScreen, type Severity } from '../desk';

export const TAGS = ['Size', 'Position', 'Colour', 'Outline', 'Text size', 'Words', 'Font', 'Spacing', 'Art', 'Missing', 'Remove'];
// which checker misses point at which tag (shown as a dashed hint on the tag button)
const HINTS: [RegExp, string][] = [
  [/: [xy] -?\d/, 'Position'], [/: [wh] -?\d/, 'Size'], [/: fill |text colour/, 'Colour'], [/: border |text outline/, 'Outline'],
  [/letter height/, 'Text size'], [/words|no text found|no readable text/, 'Words'], [/: font /, 'Font'], [/: art /, 'Art'],
  [/MISSING/, 'Missing'],
];
type Mode = 'side' | 'onion' | 'blink' | 'wipe';
type Side = 'proposal' | 'build';
type Status = 'pass' | 'miss' | 'missing' | 'unchecked';
type View = { s: number; x: number; y: number };
type Sel = { type: 'el'; id: string } | { type: 'pin'; id: string } | { type: 'newpin'; x: number; y: number; side: Side } | null;
type Form = { tags: string[]; note: string; severity: Severity; should: string };
const EMPTY: Form = { tags: [], note: '', severity: 'must', should: '' };
const COLOR: Record<Status, string> = { pass: '#22c55e', miss: '#ef4444', missing: '#d4d4d8', unchecked: '#d4d4d8' };
const STATUS_WORD: Record<Status, string> = { pass: 'within tolerance', miss: 'miss', missing: 'not built', unchecked: 'not checked' };

const hex = (c?: number[] | null) => (c && c.length >= 3 ? '#' + c.slice(0, 3).map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('').toUpperCase() : null);
const f1 = (v: unknown, d = 1) => (typeof v === 'number' && isFinite(v) ? v.toFixed(d) : '-');
const shortAt = (at?: string) => (at ? at.slice(5, 16).replace('T', ' ') : '');
const area = (b: Box) => b[2] * b[3];
const inside = (b: Box, x: number, y: number) => x >= b[0] && x <= b[0] + b[2] && y >= b[1] && y <= b[1] + b[3];
/** a box in window A's picture -> the same place in window B's picture (both window boxes in % of their own picture) */
const remap = (b: Box, a: Box, z: Box): Box => [z[0] + (b[0] - a[0]) * z[2] / a[2], z[1] + (b[1] - a[1]) * z[3] / a[3], b[2] * z[2] / a[2], b[3] * z[3] / a[3]];
const openCount = (s?: MenuFeedback['screens'][string]) =>
  s ? Object.values(s.elements || {}).flat().filter((n) => n.status !== 'done').length + (s.pins || []).filter((p) => p.status !== 'done').length : 0;

declare global { interface Window { __lastMenuSave?: MenuOpResult } }

export function useMenuFeedback() {
  const [fb, setFb] = useState<MenuFeedback>({ screens: {} });
  useEffect(() => { desk.menuFeedback.load().then((d) => setFb(d && d.screens ? d : { screens: {} })).catch(() => {}); }, []);
  const op = useCallback(async (o: MenuOp) => {
    try {
      const r = await desk.menuFeedback.op(o);
      window.__lastMenuSave = r;
      setFb(r.data);
      toast(r.smoke ? 'Smoke test: note kept in memory, file not written' : 'Saved to docs/feedback/menu-feedback.json');
      return r;
    } catch (e) { toast('Could not save: ' + String(e)); return null; }
  }, []);
  return { fb, op };
}

function useSize(ref: RefObject<HTMLElement | null>) {
  const [s, setS] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setS({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [ref]);
  return s;
}

type Drawn = { id: string; box: Box; status: Status; ghost?: boolean; notes: number };
type PinDot = { id: string; n: number; x: number; y: number; done: boolean };

/** one picture with its boxes and pins, inside a zoom/pan viewport (the view is shared, so both pictures move together) */
type Rect = { l: number; t: number; w: number; h: number };
function Pane({ side, label, rect, view, setView, onPick, onHover, children, testId }: {
  side: Side; label: ReactNode; rect: Rect; view: View; setView: (v: View) => void;
  onPick: (side: Side, x: number, y: number, forcePin: boolean) => void; onHover: (side: Side, x: number, y: number) => void;
  children: ReactNode; testId: string;
}) {
  const vp = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const drag = useRef<{ cx: number; cy: number; x: number; y: number; moved: boolean } | null>(null);
  const viewRef = useRef(view);
  viewRef.current = view;
  const pct = (cx: number, cy: number) => {
    const r = sheet.current!.getBoundingClientRect();
    return [((cx - r.left) / r.width) * 100, ((cy - r.top) / r.height) * 100];
  };
  useEffect(() => {
    const el = vp.current!;
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      const v = viewRef.current;
      const s = Math.max(0.5, Math.min(16, v.s * Math.exp(-e.deltaY * 0.0015)));
      const mx = e.clientX - r.left, my = e.clientY - r.top;
      setView({ s, x: mx - ((mx - v.x) * s) / v.s, y: my - ((my - v.y) * s) / v.s });
    };
    el.addEventListener('wheel', wheel, { passive: false });
    return () => el.removeEventListener('wheel', wheel);
  }, [setView]);
  return (
    <div className="flex min-w-0 flex-1 flex-col" data-side={side}>
      <div className="flex h-6 shrink-0 items-center gap-2 px-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</div>
      <div ref={vp} data-viewport={testId} className="relative min-h-0 flex-1 cursor-crosshair overflow-hidden rounded-md border bg-[#101013]"
        onPointerDown={(e) => {
          if (e.button !== 0 && e.button !== 1) return;
          drag.current = { cx: e.clientX, cy: e.clientY, x: view.x, y: view.y, moved: false };
          try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
        }}
        onPointerMove={(e) => {
          const d = drag.current;
          if (d) {
            const dx = e.clientX - d.cx, dy = e.clientY - d.cy;
            if (!d.moved && Math.abs(dx) + Math.abs(dy) > 4) d.moved = true;
            if (d.moved) setView({ ...viewRef.current, x: d.x + dx, y: d.y + dy });
          } else if (sheet.current) { const [x, y] = pct(e.clientX, e.clientY); onHover(side, x, y); }
        }}
        onPointerUp={(e) => {
          const d = drag.current; drag.current = null;
          if (d && !d.moved && e.button === 0 && sheet.current) { const [x, y] = pct(e.clientX, e.clientY); onPick(side, x, y, e.shiftKey || e.altKey); }
        }}
        onPointerLeave={() => onHover(side, -1, -1)}>
        <div className="absolute inset-0 origin-top-left" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.s})` }}>
          <div ref={sheet} data-sheet={testId} className="absolute" style={{ width: rect.w, height: rect.h, left: rect.l, top: rect.t }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

function Boxes({ items, sel, hover, s }: { items: Drawn[]; sel?: string; hover?: string | null; s: number }) {
  return (
    <div className="pointer-events-none absolute inset-0">
      {[...items].sort((a, b) => area(b.box) - area(a.box)).map((d) => {
        const on = d.id === sel, hv = d.id === hover;
        return (
          <div key={d.id} data-box={d.id} data-status={d.status} className="absolute"
            style={{ left: d.box[0] + '%', top: d.box[1] + '%', width: d.box[2] + '%', height: d.box[3] + '%',
              border: `${(on ? 2.5 : hv ? 2 : 1.25) / s}px ${d.ghost ? 'dashed' : 'solid'} ${COLOR[d.status]}`,
              boxShadow: on ? `0 0 0 ${1.5 / s}px #fff, 0 0 ${10 / s}px ${COLOR[d.status]}` : `0 0 0 ${0.75 / s}px rgba(0,0,0,.55), inset 0 0 0 ${0.75 / s}px rgba(0,0,0,.55)`,   // dark halo: lines read on any art
              background: on ? COLOR[d.status] + '22' : undefined, opacity: d.ghost && !on ? 0.75 : 1 }}>
            {(on || hv) && (
              <span className="absolute left-0 whitespace-nowrap rounded-sm px-1 font-medium text-black"
                style={{ bottom: '100%', marginBottom: 2 / s, fontSize: 11 / s, background: COLOR[d.status] }}>{d.id}</span>
            )}
            {d.notes > 0 && (
              <span className="absolute flex items-center justify-center rounded-full bg-change font-bold text-black"
                style={{ right: -7 / s, top: -7 / s, width: 14 / s, height: 14 / s, fontSize: 9 / s }}>{d.notes}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Pins({ pins, sel, s, onOpen }: { pins: PinDot[]; sel?: string; s: number; onOpen: (id: string) => void }) {
  return (
    <div className="pointer-events-none absolute inset-0">
      {pins.map((p) => (
        <button key={p.id} data-pin={p.id} title={'Pin ' + p.n}
          className={cn('pointer-events-auto absolute flex items-center justify-center rounded-full border-black font-bold text-black',
            p.done ? 'bg-zinc-400' : 'bg-change', p.id === sel && 'ring-white')}
          style={{ left: p.x + '%', top: p.y + '%', width: 20 / s, height: 20 / s, fontSize: 10 / s, borderWidth: 1.5 / s,
            transform: 'translate(-50%, -50%)', boxShadow: p.id === sel ? `0 0 0 ${2 / s}px #fff` : undefined }}
          onPointerDown={(e) => e.stopPropagation()} onPointerUp={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onOpen(p.id); }}>{p.n || '+'}</button>
      ))}
    </div>
  );
}

/** a large crop of one picture around a box (box in % of the picture) */
function Crop({ src, size, box, color, label, W = 196, H = 150 }: { src?: string | null; size?: [number, number] | null; box?: Box | null;
  color: string; label: string; W?: number; H?: number }) {
  let body: ReactNode = <div className="flex size-full items-center justify-center text-xs text-muted-foreground">not in the build</div>;
  if (src && size && box) {
    const [IW, IH] = size;
    const bx = (box[0] / 100) * IW, by = (box[1] / 100) * IH, bw = Math.max(2, (box[2] / 100) * IW), bh = Math.max(2, (box[3] / 100) * IH);
    const pad = 0.18 * Math.max(bw, bh);
    const k = Math.min(W / (bw + 2 * pad), H / (bh + 2 * pad));
    const left = W / 2 - (bx + bw / 2) * k, top = H / 2 - (by + bh / 2) * k;
    body = (
      <>
        <img src={desk.media(src)} alt="" draggable={false} className="absolute max-w-none" style={{ left, top, width: IW * k, height: IH * k }} />
        <div className="absolute" style={{ left: left + bx * k, top: top + by * k, width: bw * k, height: bh * k, border: `1px dashed ${color}` }} />
      </>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
      <div className="relative overflow-hidden rounded-md border bg-[#101013]" style={{ width: W, height: H }}>{body}</div>
    </div>
  );
}

function Swatch({ c }: { c: string | null }) {
  if (!c) return <span>-</span>;
  return <span className="inline-flex items-center gap-1"><span className="inline-block size-3 rounded-sm border" style={{ background: c }} />{c}</span>;
}

function Measures({ el, row }: { el?: MenuScreen['elements'][number]; row?: MenuRow }) {
  const r = row?.ref || {}, g = row?.game || {}, gui = (row?.gui || {}) as Record<string, unknown>;
  const miss = (re: RegExp) => !!row?.misses?.some((m) => re.test(m));
  const lines: { k: string; a: ReactNode; b: ReactNode; bad: boolean }[] = [];
  const add = (k: string, a: ReactNode, b: ReactNode, re: RegExp, show = true) => { if (show) lines.push({ k, a, b, bad: miss(re) }); };
  add('Box x, y, w, h %', row?.box_ref?.map((v) => f1(v)).join(', ') ?? '-', row?.box_game?.map((v) => f1(v)).join(', ') ?? '-', /: [xywh] -?\d/, !!row?.box_ref);
  add('Fill', <Swatch c={hex(r.fill) || el?.fill || null} />, <Swatch c={hex(g.fill) || (gui.backgroundColor as string) || null} />, /: fill /, !!(r.fill || g.fill));
  add('Border % h (px)', r.border ? `${f1(r.border.pct_h, 2)} (${r.border.px})` : '-', g.border ? `${f1(g.border.pct_h, 2)} (${g.border.px})` : '-', /: border /, !!(r.border || g.border));
  add('Corner % of side', f1(r.corner?.pct, 0), f1(g.corner?.pct, 0) + (gui.corner != null ? ` (UICorner ${String(gui.corner)})` : ''), /: corner /, !!(r.corner || g.corner));
  add('Text height % h', f1(r.text?.cap_pct_h), f1(g.text?.cap_pct_h) + (gui.textSize != null ? ` (size ${String(gui.textSize)})` : ''), /letter height/, !!(r.text || g.text || el?.kind === 'text'));
  add('Text colour', <Swatch c={hex(r.text?.fill) || el?.color || null} />, <Swatch c={hex(g.text?.fill) || (gui.textColor as string) || null} />, /text colour/, !!(r.text || g.text));
  add('Outline px (colour)', r.text ? <span>{r.text.stroke_px} <Swatch c={hex(r.text.stroke_col)} /></span> : '-',
    g.text ? <span>{g.text.stroke_px}{gui.stroke != null ? ` (UIStroke ${String(gui.stroke)})` : ''} <Swatch c={hex(g.text.stroke_col) || (gui.strokeColor as string) || null} /></span> : '-',
    /text outline/, !!(r.text || g.text));
  add('Art size w x h %', r.image ? `${f1(r.image.w_pct)} x ${f1(r.image.h_pct)}` : '-', g.image ? `${f1(g.image.w_pct)} x ${f1(g.image.h_pct)}` : '-', /: art /, !!(r.image || g.image));
  const words = (gui.text ?? gui.innerText ?? (row?.words ? Object.values(row.words)[0] : undefined)) as string | undefined;
  add('Words', el?.text || (el?.words || el?.words_text ? `/${el?.words || el?.words_text}/` : '-'), words ?? '-', /words|no text found|no readable text/, !!(el?.words || el?.words_text || el?.text || words));
  add('Font', el?.font || '-', (gui.font as string) || '-', /: font /, !!(el?.font || gui.font));
  if (!lines.length) return null;
  return (
    <table className="w-full text-xs" data-measures>
      <thead><tr className="text-left text-[10px] uppercase tracking-wide text-muted-foreground"><th className="py-1 font-semibold" /><th className="font-semibold">Proposal</th><th className="font-semibold">Build</th></tr></thead>
      <tbody>
        {lines.map((l) => (
          <tr key={l.k} className={cn('border-t', l.bad && 'bg-cut/15 text-[#fca5a5]')} data-bad={l.bad || undefined}>
            <td className="py-1 pr-2 text-muted-foreground">{l.k}</td><td className="pr-2">{l.a}</td><td>{l.b}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function NoteForm({ form, setForm, hints, onSave, saveLabel }: { form: Form; setForm: (f: Form) => void; hints: Set<string>; onSave: () => void; saveLabel: string }) {
  return (
    <div className="flex flex-col gap-2" data-note-form>
      <div className="flex flex-wrap gap-1">
        {TAGS.map((t, i) => {
          const on = form.tags.includes(t);
          return (
            <Button key={t} variant="outline" size="xs" data-tag={t}
              className={cn(on && 'border-change bg-change/20 text-change', !on && hints.has(t) && 'border-dashed border-cut/80')}
              title={hints.has(t) ? 'The checker found a miss of this kind' : undefined}
              onClick={() => setForm({ ...form, tags: on ? form.tags.filter((x) => x !== t) : [...form.tags, t] })}>
              {i < 9 && <Kbd className="h-4 min-w-4 bg-transparent px-0.5 text-[10px]">{i + 1}</Kbd>}{t}
            </Button>
          );
        })}
      </div>
      <Textarea data-note-input rows={3} value={form.note} placeholder="What is wrong? e.g. outline too thin, like the proposal (Enter saves, Shift+Enter new line)"
        className="text-sm" onChange={(e) => setForm({ ...form, note: e.target.value })} />
      <div className="flex items-center gap-2">
        <ToggleGroup type="single" size="sm" variant="outline" value={form.severity} onValueChange={(v) => v && setForm({ ...form, severity: v as Severity })}>
          <ToggleGroupItem value="must" className="px-2 text-xs" data-sev="must">Must fix</ToggleGroupItem>
          <ToggleGroupItem value="nice" className="px-2 text-xs" data-sev="nice">Nice to have</ToggleGroupItem>
        </ToggleGroup>
        <Input data-should-input value={form.should} placeholder="Should be (optional), e.g. #FFE04A, 3 px"
          className="h-8 flex-1 text-xs" onChange={(e) => setForm({ ...form, should: e.target.value })} />
      </div>
      <Button size="sm" data-save-note disabled={!form.tags.length && !form.note.trim()} onClick={onSave}>
        <Check />{saveLabel}<Kbd className="h-4 bg-transparent px-1 text-[10px] text-primary-foreground/70">Enter</Kbd>
      </Button>
    </div>
  );
}

function NoteList({ notes, onRemove, onStatus }: { notes: (MenuNote & { n?: number })[]; onRemove: (id: string) => void; onStatus: (id: string, s: 'open' | 'done') => void }) {
  if (!notes.length) return null;
  return (
    <div className="flex flex-col gap-1.5" data-note-list>
      {notes.map((n) => (
        <div key={n.id} className={cn('rounded-md border p-2 text-xs', n.status === 'done' && 'opacity-60')}>
          <div className="flex items-center gap-1.5">
            <span className={cn('rounded-sm px-1 text-[10px] font-semibold uppercase', n.severity === 'nice' ? 'bg-muted' : 'bg-cut/30 text-[#fca5a5]')}>
              {n.severity === 'nice' ? 'nice to have' : 'must fix'}</span>
            <span className="font-medium">{n.tags.join(', ') || 'Note'}</span>
            <span className="ml-auto text-[10px] text-muted-foreground">{n.status === 'done' ? `done${n.commit ? ' ' + n.commit.slice(0, 8) : ''}` : 'open'} · {shortAt(n.at)}</span>
            <Button variant="ghost" size="icon-xs" title={n.status === 'done' ? 'Open again' : 'Mark done'} onClick={() => onStatus(n.id, n.status === 'done' ? 'open' : 'done')}>
              {n.status === 'done' ? <RotateCcw /> : <Check />}</Button>
            <Button variant="ghost" size="icon-xs" title="Delete this note" onClick={() => onRemove(n.id)}><Trash2 /></Button>
          </div>
          {n.note && <p className="mt-1 whitespace-pre-wrap">{n.note}</p>}
          {n.should && <p className="mt-0.5 text-muted-foreground">Should be: {n.should}</p>}
        </div>
      ))}
    </div>
  );
}

export default function Menus({ menus }: { menus: MenuScreen[] }) {
  const [idx, setIdx] = useState(0);
  const [mode, setMode] = useState<Mode>('side');
  const [blinkB, setBlinkB] = useState(true);
  const [wipe, setWipe] = useState(50);
  const [view, setView] = useState<View>({ s: 1, x: 0, y: 0 });
  const [pinMode, setPinMode] = useState(false);
  const [sel, setSel] = useState<Sel>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [form, setForm] = useState<Form>(EMPTY);
  const { fb, op } = useMenuFeedback();
  const stage = useRef<HTMLDivElement>(null);
  const size = useSize(stage);

  const m = menus[Math.min(idx, menus.length - 1)];
  const last = m?.latest || null;
  const rows = useMemo(() => Object.fromEntries((last?.rows || []).map((r) => [r.id, r])) as Record<string, MenuRow>, [last]);
  const scr = (m && fb.screens[m.screen]) || { elements: {}, pins: [] };
  const els = m?.elements || [];
  const winP = els.find((e) => e.id === 'window')?.pct || null;
  const winG = rows.window?.pct_game || null;
  const shot = last?.shot || null;
  const canOverlay = !!shot && !!winP && !!winG;   // onion / blink / wipe need both windows to line the pictures up
  const aP = m?.proposal_size ? m.proposal_size[0] / m.proposal_size[1] : 16 / 9;
  const aG = last?.shot_size ? last.shot_size[0] / last.shot_size[1] : aP;
  const status = (id: string): Status => rows[id]?.status || 'unchecked';
  const notesOf = (id: string) => (scr.elements[id] || []).filter((n) => n.status !== 'done').length;

  const propBoxes: Drawn[] = els.filter((e) => e.pct).map((e) => ({ id: e.id, box: e.pct!, status: status(e.id), ghost: !rows[e.id] || rows[e.id].status === 'missing', notes: notesOf(e.id) }));
  const buildBoxes: Drawn[] = shot ? els.flatMap((e) => {
    const r = rows[e.id];
    if (r?.pct_game) return [{ id: e.id, box: r.pct_game, status: status(e.id), notes: notesOf(e.id) }];
    if (e.pct && winP && winG) return [{ id: e.id, box: remap(e.pct, winP, winG), status: status(e.id), ghost: true, notes: notesOf(e.id) }];
    return [];
  }) : [];
  // pins are stored in % of their side's window; drawn in % of the picture
  const toPic = (side: Side, x: number, y: number): [number, number] => {
    const w = side === 'proposal' ? winP : winG;
    return w ? [w[0] + (x / 100) * w[2], w[1] + (y / 100) * w[3]] : [x, y];
  };
  const toWin = (side: Side, x: number, y: number): [number, number] => {
    const w = side === 'proposal' ? winP : winG;
    return w ? [((x - w[0]) / w[2]) * 100, ((y - w[1]) / w[3]) * 100] : [x, y];
  };
  const pinDots = (side: Side, overlay = false): PinDot[] => {
    const out: PinDot[] = [];
    scr.pins.forEach((p, i) => {
      if (!overlay && p.side !== side) return;
      let [x, y] = toPic(p.side, p.x, p.y);
      if (overlay && p.side === 'build' && winP && winG) [x, y] = remap([x, y, 0, 0], winG, winP);
      out.push({ id: p.id, n: i + 1, x, y, done: p.status === 'done' });
    });
    if (sel?.type === 'newpin' && (overlay || sel.side === side)) {
      let [x, y] = toPic(sel.side, sel.x, sel.y);
      if (overlay && sel.side === 'build' && winP && winG) [x, y] = remap([x, y, 0, 0], winG, winP);
      out.push({ id: '__new', n: 0, x, y, done: false });
    }
    return out;
  };

  const hit = (side: Side, x: number, y: number) => {
    const list = side === 'proposal' ? propBoxes : buildBoxes;
    const c = list.filter((d) => inside(d.box, x, y)).sort((a, b) => area(a.box) - area(b.box));
    return c[0]?.id || null;
  };
  const choose = useCallback((s: Sel) => { setSel(s); setForm(EMPTY); }, []);
  const onPick = (side: Side, x: number, y: number, forcePin: boolean) => {
    const id = forcePin || pinMode ? null : hit(side, x, y);
    if (id) { choose({ type: 'el', id }); return; }
    if (x < 0 || y < 0 || x > 100 || y > 100) return;
    const [wx, wy] = toWin(side, x, y);
    choose({ type: 'newpin', x: wx, y: wy, side });
  };
  const onHover = (side: Side, x: number, y: number) => setHover(x < 0 ? null : hit(side, x, y));

  const save = useCallback(async () => {
    if (!m || !sel || sel.type === 'pin' || (!form.tags.length && !form.note.trim())) return;
    const fields = { ...form, note: form.note.trim(), check: last?.at || '' };
    const target = sel.type === 'el' ? { element: sel.id } : { x: sel.x, y: sel.y, side: sel.side };
    const r = await op({ kind: 'add', screen: m.screen, target, fields });
    if (!r) return;
    setForm(EMPTY);
    if (sel.type === 'newpin') {
      const pins = r.data.screens[m.screen]?.pins || [];
      if (pins.length) setSel({ type: 'pin', id: pins[pins.length - 1].id });
    }
  }, [m, sel, form, last, op]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const typing = t.tagName === 'TEXTAREA' || t.tagName === 'INPUT';
      if (e.key === 'Escape') { if (typing) t.blur(); setSel(null); e.preventDefault(); return; }
      if (e.key === 'Enter' && !e.shiftKey && sel && sel.type !== 'pin') { e.preventDefault(); save(); return; }
      if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === 'b' && canOverlay) { if (mode !== 'blink') { setMode('blink'); setBlinkB(true); } else setBlinkB((v) => !v); e.preventDefault(); }
      else if (k === 'p') { setPinMode((v) => !v); e.preventDefault(); }
      else if (k === 'f') { (document.querySelector('[data-fit]') as HTMLElement | null)?.click(); e.preventDefault(); }
      else if (/^[1-9]$/.test(e.key) && sel && sel.type !== 'pin') {
        const tag = TAGS[Number(e.key) - 1];
        setForm((f) => ({ ...f, tags: f.tags.includes(tag) ? f.tags.filter((x) => x !== tag) : [...f.tags, tag] }));
        e.preventDefault();
      }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [sel, save, mode, canOverlay]);

  // stage geometry: the proposal fitted into its pane; the build scaled and placed so its menu WINDOW lands exactly on the proposal's
  // window (same size, same place: zoom and pan stay locked on the same spot); no window in the build = same height, centred
  const side = mode === 'side' || !canOverlay;
  const paneW = side ? (size.w - 8) / 2 : size.w, paneH = Math.max(0, size.h - 24);
  const hP = Math.max(50, Math.min(paneH - 16, (paneW - 16) / aP));
  const rectP: Rect = { w: hP * aP, h: hP, l: (paneW - hP * aP) / 2, t: (paneH - hP) / 2 };
  const hG = Math.max(50, Math.min(paneH - 16, (paneW - 16) / aG));
  let rectG: Rect = { w: hG * aG, h: hG, l: (paneW - hG * aG) / 2, t: (paneH - hG) / 2 };
  if (winP && winG) {
    const gW = (rectP.w * winP[2]) / winG[2], gH = gW / aG;
    rectG = { w: gW, h: gH, l: rectP.l + (winP[0] / 100) * rectP.w - (winG[0] / 100) * gW, t: rectP.t + (winP[1] / 100) * rectP.h - (winG[1] / 100) * gH };
  }
  const fitMenu = (): View => {   // zoom onto the spec elements (window + rail) instead of the whole board picture
    const bs = els.map((e) => e.pct).filter(Boolean) as Box[];
    if (!bs.length || !paneW || !paneH) return { s: 1, x: 0, y: 0 };
    const x0 = Math.min(...bs.map((b) => b[0])), y0 = Math.min(...bs.map((b) => b[1]));
    const x1 = Math.max(...bs.map((b) => b[0] + b[2])), y1 = Math.max(...bs.map((b) => b[1] + b[3]));
    const ux = rectP.l + (x0 / 100) * rectP.w, uy = rectP.t + (y0 / 100) * rectP.h, uw = ((x1 - x0) / 100) * rectP.w, uh = ((y1 - y0) / 100) * rectP.h;
    const sc = Math.max(1, Math.min(16, 0.92 * Math.min(paneW / uw, paneH / uh)));
    return { s: sc, x: paneW / 2 - (ux + uw / 2) * sc, y: paneH / 2 - (uy + uh / 2) * sc };
  };
  // fit on a new screen or mode; on a pane resize (the note panel opening) refit only while the owner has not zoomed or panned
  const fitted = useRef({ k: '', size: '' });
  const manual = useRef(false);
  const userView = useCallback((v: View) => { manual.current = true; setView(v); }, []);
  useEffect(() => {
    if (size.w <= 0) return;
    const k = `${idx}-${side}`, sz = `${Math.round(paneW)}x${Math.round(paneH)}`;
    if (fitted.current.k !== k || (fitted.current.size !== sz && !manual.current)) {
      fitted.current = { k, size: sz }; manual.current = false; setView(fitMenu());
    }
  });

  if (!m) return <p className="p-5 text-sm text-muted-foreground">No menu specs yet (docs/menu-specs/&lt;screen&gt;/spec.json).</p>;
  const fit: Box | null = !side && winP && winG ? [winP[0] - (winG[0] * winP[2]) / winG[2], winP[1] - (winG[1] * winP[3]) / winG[3], (100 * winP[2]) / winG[2], (100 * winP[3]) / winG[3]] : [0, 0, 100, 100];
  const selId = sel?.type === 'el' ? sel.id : sel?.type === 'pin' ? sel.id : sel?.type === 'newpin' ? '__new' : undefined;
  const counts = { pass: 0, miss: 0, grey: 0 };
  for (const e of els) { const s = status(e.id); if (s === 'pass') counts.pass++; else if (s === 'miss') counts.miss++; else counts.grey++; }
  const order: Record<Status, number> = { miss: 0, missing: 1, unchecked: 2, pass: 3 };
  const list = [...els].sort((a, b) => order[status(a.id)] - order[status(b.id)]);

  const selEl = sel?.type === 'el' ? els.find((e) => e.id === sel.id) : undefined;
  const selRow = sel?.type === 'el' ? rows[sel.id] : undefined;
  const selPin = sel?.type === 'pin' ? scr.pins.find((p) => p.id === sel.id) : undefined;
  const pinIndex = selPin ? scr.pins.indexOf(selPin) + 1 : 0;
  const hints = new Set<string>();
  for (const msg of selRow?.misses || []) for (const [re, t] of HINTS) if (re.test(msg)) hints.add(t);

  const overlaySheet = (
    <>
      <img src={desk.media(m.proposal)} alt="proposal" draggable={false} className="absolute inset-0 size-full" />
      {shot && fit && (
        <div className="absolute inset-0 overflow-hidden"
          style={{ opacity: mode === 'onion' ? 0.5 : mode === 'blink' ? (blinkB ? 1 : 0) : 1, clipPath: mode === 'wipe' ? `inset(0 0 0 ${wipe}%)` : undefined }}>
          <img src={desk.media(shot)} alt="build" draggable={false} className="absolute max-w-none"
            style={{ left: fit[0] + '%', top: fit[1] + '%', width: fit[2] + '%', height: fit[3] + '%' }} />
        </div>
      )}
      {mode === 'wipe' && <div className="pointer-events-none absolute inset-y-0 w-px bg-white" style={{ left: wipe + '%' }} />}
      <Boxes items={propBoxes} sel={selId} hover={hover} s={view.s} />
      <Pins pins={pinDots('proposal', true)} sel={selId} s={view.s} onOpen={(id) => id !== '__new' && choose({ type: 'pin', id })} />
    </>
  );

  return (
    <div className="grid min-h-0 grid-cols-[220px_1fr]" data-menus>
      <aside className="flex min-h-0 flex-col border-r">
        <div className="flex flex-col gap-1 border-b p-2">
          {menus.map((s, i) => {
            const n = openCount(fb.screens[s.screen]);
            return (
              <button key={s.screen} data-screen={s.screen} onClick={() => { setIdx(i); setSel(null); }}
                className={cn('flex gap-2 rounded-md p-1.5 text-left hover:bg-accent', i === idx && 'bg-accent')}>
                <img src={desk.media(s.proposal)} alt="" className="h-10 w-16 shrink-0 rounded-sm object-cover" />
                <span className="flex min-w-0 flex-col text-xs">
                  <span className="truncate font-medium">{s.screen}</span>
                  <span className={cn('text-[11px]', s.latest && !s.latest.sample ? (s.latest.misses.length ? 'text-[#fca5a5]' : 'text-ok') : 'text-muted-foreground')}>
                    {s.latest && !s.latest.sample ? `${s.latest.misses.length} misses · ${shortAt(s.latest.at)}` : s.latest ? 'no check yet · build picture' : 'no check yet'}</span>
                  <span className="text-[11px] text-muted-foreground">{n} owner note{n === 1 ? '' : 's'}</span>
                </span>
              </button>
            );
          })}
        </div>
        <div className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Elements</div>
        <div className="min-h-0 flex-1 overflow-y-auto py-1">
          {list.map((e) => {
            const st = status(e.id), n = notesOf(e.id);
            return (
              <button key={e.id} data-el-item={e.id} onClick={() => choose({ type: 'el', id: e.id })}
                onMouseEnter={() => setHover(e.id)} onMouseLeave={() => setHover(null)}
                className={cn('flex w-full items-center gap-2 px-3 py-1 text-left text-xs hover:bg-accent', sel?.type === 'el' && sel.id === e.id && 'bg-accent')}>
                <span className="size-2 shrink-0 rounded-full" style={{ background: COLOR[st] }} />
                <span className="truncate">{e.id}</span>
                {!!rows[e.id]?.misses?.length && <span className="ml-auto text-[10px] text-[#fca5a5]">{rows[e.id].misses.length}</span>}
                {n > 0 && <span className={cn('rounded-sm bg-change px-1 text-[10px] font-bold text-black', !rows[e.id]?.misses?.length && 'ml-auto')}>{n}</span>}
              </button>
            );
          })}
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0">
        <div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <ToggleGroup type="single" size="sm" variant="outline" value={canOverlay ? mode : 'side'} onValueChange={(v) => v && setMode(v as Mode)}>
              {(['side', 'onion', 'blink', 'wipe'] as Mode[]).map((md) => (
                <ToggleGroupItem key={md} value={md} data-mode={md} disabled={!canOverlay && md !== 'side'} className="px-2 text-xs">
                  {md === 'side' ? 'Side by side' : md === 'onion' ? 'Onion 50 %' : md === 'blink' ? 'Blink (B)' : 'Wipe'}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            {mode === 'blink' && shot && <Button variant="outline" size="sm" onClick={() => setBlinkB((v) => !v)}>Showing {blinkB ? 'BUILD' : 'PROPOSAL'}</Button>}
            {mode === 'wipe' && shot && <input type="range" min={0} max={100} value={wipe} onChange={(e) => setWipe(Number(e.target.value))} className="w-40" data-wipe />}
            <Button variant={pinMode ? 'default' : 'outline'} size="sm" data-pin-mode onClick={() => setPinMode((v) => !v)} title="Every click drops a pin (P)">
              <MapPin />Pin mode<Kbd className="h-4 bg-transparent px-1 text-[10px]">P</Kbd></Button>
            <Button variant="ghost" size="sm" data-fit onClick={() => { manual.current = false; setView(fitMenu()); }} title="Zoom onto the menu (F)">Fit menu<Kbd className="h-4 bg-transparent px-1 text-[10px]">F</Kbd></Button>
            <Button variant="ghost" size="sm" onClick={() => { manual.current = true; setView({ s: 1, x: 0, y: 0 }); }} title="The whole picture">Whole picture</Button>
            <span className="text-muted-foreground">{Math.round(view.s * 100)} %</span>
            <span className="ml-auto flex items-center gap-3 text-muted-foreground">
              <span><span className="mr-1 inline-block size-2 rounded-full bg-[#22c55e]" />{counts.pass} ok</span>
              <span><span className="mr-1 inline-block size-2 rounded-full bg-[#ef4444]" />{counts.miss} miss</span>
              <span><span className="mr-1 inline-block size-2 rounded-full bg-[#d4d4d8]" />{counts.grey} not built</span>
              <span title={last?.report ?? undefined}>{last?.sample ? 'no check yet: build picture only, run tools/menu_spec_check.py for boxes' : last ? `check ${shortAt(last.at)}${last.step ? ' · step ' + last.step : ''}${last.self_test ? ' · self-test' : ''}` : 'no check yet: run tools/menu_spec_check.py'}</span>
            </span>
          </div>
          <div ref={stage} className="flex min-h-0 flex-1 gap-2" data-stage>
            {size.w > 0 && (side ? (
              <>
                <Pane side="proposal" testId="proposal" label="Proposal" rect={rectP} view={view} setView={userView} onPick={onPick} onHover={onHover}>
                  <img src={desk.media(m.proposal)} alt="proposal" draggable={false} className="absolute inset-0 size-full" />
                  <Boxes items={propBoxes} sel={selId} hover={hover} s={view.s} />
                  <Pins pins={pinDots('proposal')} sel={selId} s={view.s} onOpen={(id) => id !== '__new' && choose({ type: 'pin', id })} />
                </Pane>
                <Pane side="build" testId="build" label={<>Build {shot && <span className="font-normal normal-case">{shot}</span>}</>} rect={rectG} view={view} setView={userView} onPick={onPick} onHover={onHover}>
                  {shot ? <img src={desk.media(shot)} alt="build" draggable={false} className="absolute inset-0 size-full" />
                    : <div className="flex size-full items-center justify-center rounded-md border border-dashed text-xs text-muted-foreground">No build capture yet</div>}
                  <Boxes items={buildBoxes} sel={selId} hover={hover} s={view.s} />
                  <Pins pins={pinDots('build')} sel={selId} s={view.s} onOpen={(id) => id !== '__new' && choose({ type: 'pin', id })} />
                </Pane>
              </>
            ) : (
              <Pane side="proposal" testId="overlay" label={mode === 'wipe' ? 'Proposal | Build' : mode === 'blink' ? (blinkB ? 'Build (B = proposal)' : 'Proposal (B = build)') : 'Proposal + build 50 %'}
                rect={rectP} view={view} setView={userView} onPick={onPick} onHover={onHover}>
                {overlaySheet}
              </Pane>
            ))}
          </div>
        </div>

        {sel && (
          <aside className="flex w-[452px] shrink-0 flex-col gap-3 overflow-y-auto border-l p-4" data-el-panel data-el-id={sel.type === 'el' ? sel.id : undefined}
            data-pin-panel={sel.type !== 'el' || undefined}>
            <div className="flex items-center gap-2">
              {sel.type === 'el' ? (
                <>
                  <span className="size-2.5 rounded-full" style={{ background: COLOR[status(sel.id)] }} />
                  <span className="text-sm font-semibold">{sel.id}</span>
                  <span className="text-xs text-muted-foreground">{selEl?.kind} · {STATUS_WORD[status(sel.id)]}</span>
                </>
              ) : (
                <span className="text-sm font-semibold">{sel.type === 'pin' ? `Pin ${pinIndex}` : 'New pin'}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    {sel.type === 'pin' && selPin ? `${selPin.side} ${f1(selPin.x, 0)} %, ${f1(selPin.y, 0)} % of window` : sel.type === 'newpin' ? `${sel.side} ${f1(sel.x, 0)} %, ${f1(sel.y, 0)} % of window` : ''}
                  </span></span>
              )}
              <Button variant="ghost" size="icon-sm" className="ml-auto" title="Close (Esc)" onClick={() => setSel(null)}><X /></Button>
            </div>
            {sel.type === 'el' && (
              <>
                <div className="flex gap-4">
                  <Crop label="Proposal" src={m.proposal} size={m.proposal_size} box={selEl?.pct} color={COLOR[status(sel.id)]} />
                  <Crop label="Build" src={shot} size={last?.shot_size} box={selRow?.pct_game || null} color={COLOR[status(sel.id)]} />
                </div>
                {selEl?.note && <p className="text-xs text-muted-foreground">Spec: {selEl.note}</p>}
                <Measures el={selEl} row={selRow} />
                {!!selRow?.misses?.length && (
                  <ul className="flex flex-col gap-0.5 text-xs text-[#fca5a5]" data-misses>
                    {selRow.misses.map((x) => <li key={x}>{x.replace(sel.id + ': ', '')}</li>)}
                  </ul>
                )}
                {!selRow && <p className="text-xs text-muted-foreground">Not in the newest check{last?.step ? ` (step ${last.step} only)` : ''}.</p>}
                <NoteList notes={scr.elements[sel.id] || []} onRemove={(id) => op({ kind: 'remove', screen: m.screen, id })}
                  onStatus={(id, s) => op({ kind: 'update', screen: m.screen, id, fields: { status: s } })} />
                <NoteForm form={form} setForm={setForm} hints={hints} onSave={save} saveLabel="Save note" />
              </>
            )}
            {sel.type !== 'el' && (() => {
              const p = sel.type === 'pin' ? selPin : sel;
              if (!p) return null;
              const [x, y] = toPic(p.side, p.x, p.y);
              const pic = p.side === 'proposal' ? { src: m.proposal, size: m.proposal_size } : { src: shot, size: last?.shot_size };
              return (
                <>
                  <Crop label={p.side} src={pic.src} size={pic.size} box={[x - 2.5, y - 2.5, 5, 5]} color="#f59e0b" W={420} H={180} />
                  {sel.type === 'pin' && selPin ? (
                    <NoteList notes={[selPin as MenuPin]} onRemove={(id) => { op({ kind: 'remove', screen: m.screen, id }); setSel(null); }}
                      onStatus={(id, s) => op({ kind: 'update', screen: m.screen, id, fields: { status: s } })} />
                  ) : (
                    <NoteForm form={form} setForm={setForm} hints={hints} onSave={save} saveLabel="Save pin" />
                  )}
                </>
              );
            })()}
          </aside>
        )}
      </div>
    </div>
  );
}
