// Text and buttons tab (docs/247): live specimens of fonts, outline weights, label styles and button art, each one rateable.
// Text is drawn like the game draws it: a dark under-layer (outline + drop shadow) and the fill on top, fattened by a stroke
// in its own colour ("bold"). Numbers are shares of the font size, the same numbers the hatch mock and game text styles use.
import type { ReactNode } from 'react';
import { Sparkles, ThumbsDown, ThumbsUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { desk, type Feedback, type Verdict } from '../desk';
import type { Filter } from '../App';

const INK = '#1B1020';
type Word = { font?: string; size?: number; fill?: string; outline?: number; drop?: number; bold?: number };

export function Text({ t, font = "'Fredoka One'", size = 44, fill = '#fff', outline = 0.09, drop = 0.08, bold = 0.022 }: Word & { t: string }) {
  const o = outline * size, d = drop * size, b = bold * size;
  const base = { fontFamily: font, fontSize: size, fontWeight: font.includes('Nunito') ? 900 : 400, lineHeight: 1, whiteSpace: 'nowrap' as const };
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      {(outline > 0 || drop > 0) && (
        <span style={{ ...base, position: 'absolute', color: INK, WebkitTextStroke: `${2 * (o + b)}px ${INK}`, textShadow: d ? `0 ${d}px 0 ${INK}` : undefined }}>{t}</span>
      )}
      <span style={{ ...base, position: 'relative', color: fill, WebkitTextStroke: b ? `${2 * b}px ${fill}` : undefined }}>{t}</span>
    </span>
  );
}

/** a 9-sliced kit picture behind the children (outline keeps its thickness at any width) */
function Nine({ src, slice, artH, h, w, children }: { src: string; slice: number; artH: number; h: number; w: number; children: ReactNode }) {
  const bw = Math.min((slice * h) / artH, h / 2);
  return (
    <div style={{ position: 'relative', width: w, height: h }}>
      <div style={{ position: 'absolute', inset: 0, boxSizing: 'border-box', borderStyle: 'solid', borderWidth: bw,
        borderImage: `url("${desk.media(src)}") ${slice} fill stretch` }} />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', paddingBottom: h * 0.08 }}>{children}</div>
    </div>
  );
}

const FONTS: [string, string][] = [["'Fredoka One'", 'Fredoka One (game font now)'], ["'Luckiest Guy'", 'Luckiest Guy'], ["'Bangers'", 'Bangers'],
  ["'Denk One'", 'Denk One'], ["'Nunito'", 'Nunito Black']];
const BTNS: [string, string, number, number][] = [
  ['build/hatch-mock/art/btn-green.png', 'Rounded 3D (hatch proposal)', 92, 192],
  ['resources/ui/v2/shopkit2/button-green.png', 'Shop kit 2 (Aura Shop)', 38, 84],
  ['resources/ui/v2/toybox/final/button-green.png', 'Toybox kit', 40, 0],
  ['build/hatch-mock/art/btn-purple.png', 'Rounded 3D purple', 92, 192],
];

export type Specimen = { id: string; section: string; title: string; render: () => ReactNode };
export const SPECIMENS: Specimen[] = [
  ...FONTS.map(([f, name]): Specimen => ({ id: 'specimen/font/' + name, section: 'Fonts (same white word style)', title: name,
    render: () => <Text t="BEST FIND!" font={f} size={46} /> })),
  ...[0.05, 0.09, 0.13].map((o): Specimen => ({ id: 'specimen/outline/' + o, section: 'Outline weight (share of the font size)', title: `outline ${Math.round(o * 100)} %`,
    render: () => <Text t="LEGENDARY" size={44} outline={o} /> })),
  ...[0, 0.022, 0.045].map((b): Specimen => ({ id: 'specimen/bold/' + b, section: 'Letter weight (extra bold)', title: b ? `bold +${(b * 100).toFixed(1)} %` : 'no extra bold',
    render: () => <Text t="SPOTS" size={50} bold={b} /> })),
  ...[0, 0.05, 0.1].map((d): Specimen => ({ id: 'specimen/drop/' + d, section: 'Drop shadow under words', title: d ? `drop ${Math.round(d * 100)} %` : 'no drop',
    render: () => <Text t="TAP!" size={54} drop={d} /> })),
  { id: 'specimen/label/cream', section: 'Labels on chips and pills', title: 'dark on cream chip', render: () => (
    <div className="rounded-full border-[3px] px-5 py-1.5" style={{ background: '#FFF1D2', borderColor: INK }}><Text t="Egg 1 of 3" size={26} fill="#1E1A2B" outline={0} drop={0} bold={0.018} /></div>) },
  { id: 'specimen/label/pill', section: 'Labels on chips and pills', title: 'dark on rarity pill', render: () => (
    <div className="rounded-full border-[3px] px-6 py-1" style={{ background: '#5CF0FF', borderColor: INK }}><Text t="RARE" size={26} fill="#1E1A2B" outline={0} drop={0} bold={0.018} /></div>) },
  { id: 'specimen/label/white-on-pill', section: 'Labels on chips and pills', title: 'white outlined on pill', render: () => (
    <div className="rounded-full border-[3px] px-6 py-1" style={{ background: '#C77DFF', borderColor: INK }}><Text t="EPIC" size={26} /></div>) },
  ...BTNS.map(([src, name, slice, artH]): Specimen => ({ id: 'specimen/button/' + src, section: 'Buttons (same text, different kit art)', title: name,
    render: () => (artH ? <Nine src={src} slice={slice} artH={artH} h={64} w={240}><Text t="PLAY AGAIN" size={28} /></Nine>
      : <div style={{ position: 'relative', width: 240, height: 64 }}><img src={desk.media(src)} className="absolute inset-0 size-full" alt="" />
          <div className="absolute inset-0 flex items-center justify-center pb-1"><Text t="PLAY AGAIN" size={28} /></div></div>) })),
];

const ICONS: Record<Verdict, typeof ThumbsUp> = { like: ThumbsUp, dislike: ThumbsDown, upgrade: Sparkles };
const CLS: Record<Verdict, string> = { like: 'text-ok border-ok', dislike: 'text-cut border-cut', upgrade: 'text-change border-change' };

export default function Specimens({ fb, setItem, filter }: {
  fb: Feedback; setItem: (id: string, p: { verdict?: Verdict | null; note?: string }) => void; filter: Filter;
}) {
  const sections = [...new Set(SPECIMENS.map((s) => s.section))];
  return (
    <div className="flex flex-col gap-6 pt-1">
      {sections.map((sec) => (
        <div key={sec} className="flex flex-col gap-2">
          <h3 className="text-xs text-muted-foreground">{sec}</h3>
          <div className="flex flex-wrap gap-3">
            {SPECIMENS.filter((s) => s.section === sec).map((s) => {
              const v = fb.items[s.id]?.verdict;
              if (filter !== 'all' && (filter === 'unrated' ? v : v !== filter)) return null;
              return (
                <div key={s.id} className={cn('flex w-[300px] flex-col gap-2 rounded-md border p-3', v && 'ring-2', v === 'like' && 'ring-ok', v === 'dislike' && 'ring-cut', v === 'upgrade' && 'ring-change')} data-item={s.id}>
                  <div className="flex h-24 items-center justify-center rounded-md" style={{ background: '#79c76a' }}>{s.render()}</div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-muted-foreground">{s.title}</span>
                    <span className="flex gap-1">
                      {(Object.keys(ICONS) as Verdict[]).map((k) => {
                        const Icon = ICONS[k];
                        return (
                          <button key={k} title={k} onClick={() => setItem(s.id, { verdict: v === k ? null : k })}
                            className={cn('flex size-7 items-center justify-center rounded-md border text-muted-foreground hover:text-foreground', v === k && CLS[k])}>
                            <Icon className="size-3.5" />
                          </button>
                        );
                      })}
                    </span>
                  </div>
                  <input defaultValue={fb.items[s.id]?.note || ''} placeholder="Note (optional)" onBlur={(e) => setItem(s.id, { note: e.target.value.trim() })}
                    className="h-7 rounded-md border bg-transparent px-2 text-xs outline-none focus:border-ring" />
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
