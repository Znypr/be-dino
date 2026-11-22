// window.desk comes from preload.js. Shapes are owned by main.js and tools/desk_catalog.py (docs/247).
export type Item = { id: string; title: string; src: string };
export type Group = { id: string; name: string; note: string; items: Item[]; kind?: 'specimens' };
export type Tab = { name: string; groups: Group[] };
export type Catalog = { root: string; tabs: Tab[] };
export type Verdict = 'like' | 'dislike' | 'upgrade';
export type ItemFb = { verdict?: Verdict; note?: string; at?: string };
export type Feedback = { items: Record<string, ItemFb>; groups: Record<string, { note: string; at?: string }> };

type DeskApi = {
  catalog(): Promise<Catalog>;
  feedback: { load(): Promise<Feedback>; save(fb: Feedback): Promise<{ saved?: boolean; smoke?: boolean; items: number }> };
  openFile(rel: string): Promise<boolean>;
  media(rel: string): string;
  smokeShot(name: string): Promise<void>;
  smokeDone(report: unknown): Promise<void>;
};
declare global { interface Window { desk: DeskApi } }
export const desk = window.desk;

export const now = () => new Date().toISOString().slice(0, 19);
export const query = new URLSearchParams(location.search);
export const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
