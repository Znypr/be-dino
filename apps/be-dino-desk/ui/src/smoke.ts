// Smoke test (electron . --smoke): every tab renders with loaded pictures, a verdict and a detail view work; the Menus tab (BD-1301)
// renders, its compare view draws the spec boxes, clicking an element opens its panel, saving a note and a pin returns {smoke:true}.
// Never writes feedback (main.js keeps it in memory in smoke mode). BE_DINO_DESK_SHOTS=<dir> saves screenshots.
import type { Dispatch, SetStateAction } from 'react';
import { desk, wait, type Catalog, type Group, type Verdict } from './desk';
import type { Filter } from './App';

type Nav = {
  setTab: Dispatch<SetStateAction<number>>; setFilter: Dispatch<SetStateAction<Filter>>;
  setOpen: Dispatch<SetStateAction<{ group: Group; index: number } | null>>;
  setItem: (id: string, p: { verdict?: Verdict | null; note?: string }) => void;
};

export async function runSmoke(cat: Catalog, nav: Nav) {
  const report: Record<string, unknown> = { tabs: [] as unknown[] };
  let ok = cat.tabs.length >= 4;
  try {
    for (let i = 0; i < cat.tabs.length; i++) {
      nav.setTab(i);
      await wait(1500);
      const imgs = [...document.querySelectorAll('main img')] as HTMLImageElement[];
      const loaded = imgs.filter((im) => im.complete && im.naturalWidth > 0).length;
      const tiles = document.querySelectorAll('main [data-item]').length;
      (report.tabs as unknown[]).push({ tab: cat.tabs[i].name, tiles, imgs: imgs.length, loaded });
      if (!tiles) ok = false;
      if (imgs.length && !loaded) ok = false;
      await desk.smokeShot('tab-' + i + '-' + cat.tabs[i].name);
    }
    const g = cat.tabs[0].groups[0];
    nav.setTab(0); await wait(300);
    nav.setItem(g.items[0].id, { verdict: 'like', note: 'smoke' });
    nav.setOpen({ group: g, index: 0 }); await wait(800);
    report.dialog = !!document.querySelector('[role=dialog] img');
    if (!report.dialog) ok = false;
    await desk.smokeShot('detail');
    nav.setOpen(null);
    report.saved = await desk.feedback.save({ items: { [g.items[0].id]: { verdict: 'like', note: 'smoke' } }, groups: {} });
    const menus = await smokeMenus(cat, nav);
    report.menus = menus;
    if (!menus.ok) ok = false;
  } catch (e) {
    ok = false; report.error = String(e);
  }
  await desk.smokeDone({ ok, ...report });
}

const setValue = (el: HTMLTextAreaElement | HTMLInputElement, v: string) => {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
};
const clickAt = (target: Element, x: number, y: number, shift = false) => {
  for (const type of ['pointerdown', 'pointerup'])
    target.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, button: 0, pointerId: 1, isPrimary: true, shiftKey: shift }));
};
const key = (k: string) => document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }));

async function smokeMenus(cat: Catalog, nav: Nav) {
  const r: Record<string, unknown> = { ok: false };
  if (!cat.menus || !cat.menus.length) { r.error = 'no menus in the catalog'; return r; }
  nav.setTab(cat.tabs.length); await wait(1800);
  r.screens = document.querySelectorAll('[data-screen]').length;
  const prop = document.querySelector('[data-sheet="proposal"] img') as HTMLImageElement | null;
  r.proposalLoaded = !!prop && prop.complete && prop.naturalWidth > 0;
  r.boxesProposal = document.querySelectorAll('[data-side="proposal"] [data-box]').length;
  r.boxesBuild = document.querySelectorAll('[data-side="build"] [data-box]').length;
  r.checked = !!cat.menus[0].latest;
  await desk.smokeShot('menus-1-compare');
  // click an element ON the picture: the smallest box under the point wins (title, else the first text element, else any)
  const want = ['title', ...cat.menus[0].elements.filter((e) => e.kind === 'text').map((e) => e.id)];
  const box = want.map((id) => document.querySelector(`[data-side="proposal"] [data-box="${id}"]`)).find(Boolean) as HTMLElement | undefined;
  const vp = document.querySelector('[data-viewport="proposal"]');
  if (box && vp) {
    const b = box.getBoundingClientRect();
    clickAt(vp, b.left + b.width / 2, b.top + b.height / 2); await wait(600);
  }
  const panel = document.querySelector('[data-el-panel]');
  r.panel = panel?.getAttribute('data-el-id') || null;
  r.panelMeasures = !!document.querySelector('[data-el-panel] [data-measures]');
  r.panelCrops = document.querySelectorAll('[data-el-panel] img').length;
  // a note: tag key 4 (Outline), words, severity, should-be, Save -> main.js answers {smoke:true}, file untouched
  key('4'); await wait(100);
  const ta = document.querySelector('[data-note-input]') as HTMLTextAreaElement | null;
  if (ta) setValue(ta, 'smoke: outline too thin, like proposal');
  const sh = document.querySelector('[data-should-input]') as HTMLInputElement | null;
  if (sh) setValue(sh, '3 px dark');
  await wait(150);
  r.tagOn = !!document.querySelector('[data-tag="Outline"].border-change');
  window.__lastMenuSave = undefined;
  (document.querySelector('[data-save-note]') as HTMLButtonElement | null)?.click(); await wait(600);
  const saved = window.__lastMenuSave as { smoke?: boolean; saved?: boolean } | undefined;
  r.noteSave = saved ? { smoke: !!saved.smoke, saved: !!saved.saved } : null;
  r.noteListed = document.querySelectorAll('[data-el-panel] [data-note-list] > div').length;
  await desk.smokeShot('menus-2-element-panel');
  // a free pin: Shift-click inside the proposal picture, Enter saves it
  key('Escape'); await wait(200);
  const win = document.querySelector('[data-side="proposal"] [data-box="window"]') || document.querySelector('[data-sheet="proposal"]');
  if (win && vp) {
    const s = win.getBoundingClientRect();
    clickAt(vp, s.left + s.width * 0.5, s.top + s.height * 0.985, true); await wait(400);
  }
  r.pinPanel = !!document.querySelector('[data-pin-panel]');
  const ta2 = document.querySelector('[data-note-input]') as HTMLTextAreaElement | null;
  if (ta2) setValue(ta2, 'smoke: something missing here');
  await wait(100);
  window.__lastMenuSave = undefined;
  key('Enter'); await wait(600);
  const pinSaved = window.__lastMenuSave as { smoke?: boolean; saved?: boolean } | undefined;
  r.pinSave = pinSaved ? { smoke: !!pinSaved.smoke, saved: !!pinSaved.saved } : null;
  r.pinDots = document.querySelectorAll('[data-side="proposal"] [data-pin]').length;
  await desk.smokeShot('menus-3-pin');
  key('Escape'); await wait(150);
  if (r.checked) {
    (document.querySelector('[data-mode="onion"]') as HTMLElement | null)?.click(); await wait(500);
    r.onion = !!document.querySelector('[data-sheet="overlay"] img[alt="build"]');
    await desk.smokeShot('menus-4-onion');
    (document.querySelector('[data-mode="side"]') as HTMLElement | null)?.click(); await wait(200);
  }
  const ns = r.noteSave as { smoke: boolean; saved: boolean } | null, ps = r.pinSave as { smoke: boolean; saved: boolean } | null;
  r.ok = (r.screens as number) >= 1 && !!r.proposalLoaded && (r.boxesProposal as number) > 0 && (!r.checked || (r.boxesBuild as number) > 0)
    && !!r.panel && (!r.checked || !!r.panelMeasures) &&!!r.tagOn && !!ns && ns.smoke && !ns.saved && (r.noteListed as number) >= 1
    && !!r.pinPanel && !!ps && ps.smoke && !ps.saved && (r.pinDots as number) >= 1 && (!r.checked || !!r.onion);
  return r;
}
