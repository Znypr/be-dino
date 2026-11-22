// Smoke test (electron . --smoke): every tab renders with loaded pictures, a verdict and a detail view work. Never writes feedback
// (main.js returns {smoke:true} in smoke mode). BE_DINO_DESK_SHOTS=<dir> saves one screenshot per tab.
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
  } catch (e) {
    ok = false; report.error = String(e);
  }
  await desk.smokeDone({ ok, ...report });
}
