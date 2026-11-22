// window.desk comes from preload.js. Shapes are owned by main.js and tools/desk_catalog.py (docs/247).
export type Item = { id: string; title: string; src: string };
export type Group = { id: string; name: string; note: string; items: Item[]; kind?: 'specimens' };
export type Tab = { name: string; groups: Group[] };
export type Catalog = { root: string; tabs: Tab[]; menus?: MenuScreen[] };

// Menus tab (BD-1301): shapes from tools/desk_catalog.py menus() and tools/menu_spec_check.py report.json
export type Box = [number, number, number, number];   // x, y, w, h
export type Measures = {
  fill?: number[] | null; border?: { px: number; pct_h: number } | null; corner?: { pct: number | null } | null;
  text?: { cap_pct_h: number; fill: number[]; stroke_px: number; stroke_pct_h: number; stroke_col: number[] | null } | null;
  image?: { w_pct: number; h_pct: number; aspect: number } | null;
};
export type MenuEl = { id: string; kind: string; parent?: string | null; pct: Box | null; fill?: string; color?: string; text?: string;
  words?: string; words_text?: string; font?: string; note?: string };
export type MenuRow = { id: string; kind: string; status: 'pass' | 'miss' | 'missing'; misses: string[]; missing?: boolean;
  pct_ref?: Box; pct_game?: Box; box_ref?: Box; box_game?: Box; ref?: Measures; game?: Measures; fill_dE?: number;
  gui?: Record<string, unknown>; words?: Record<string, unknown>; owner?: string[]; pair?: string };
export type MenuCheck = { report: string; at: string; step: number | null; self_test: boolean; misses: string[]; shot: string | null;
  shot_size: [number, number] | null; owner_pins: unknown[]; rows: MenuRow[] };
export type MenuScreen = { screen: string; spec: string; proposal: string; proposal_size: [number, number] | null; window_px: Box;
  tolerance_pct: number; steps: { name: string; elements: string[] }[]; elements: MenuEl[]; latest: MenuCheck | null;
  history: { report: string; at: string; step: number | null; misses: number }[] };
export type Severity = 'must' | 'nice';
export type MenuNote = { id: string; tags: string[]; note: string; severity: Severity; should: string; at: string; check: string;
  status: 'open' | 'done'; commit?: string };
export type MenuPin = MenuNote & { x: number; y: number; side: 'proposal' | 'build' };
export type MenuFeedback = { screens: Record<string, { elements: Record<string, MenuNote[]>; pins: MenuPin[] }> };
export type MenuOp =
  | { kind: 'add'; screen: string; target: { element: string } | { x: number; y: number; side: 'proposal' | 'build' }; fields: Partial<MenuNote> }
  | { kind: 'update'; screen: string; id: string; fields: Partial<MenuNote> }
  | { kind: 'remove'; screen: string; id: string };
export type MenuOpResult = { data: MenuFeedback; saved?: boolean; smoke?: boolean };
export type Verdict = 'like' | 'dislike' | 'upgrade';
export type ItemFb = { verdict?: Verdict; note?: string; at?: string };
export type Feedback = { items: Record<string, ItemFb>; groups: Record<string, { note: string; at?: string }> };

type DeskApi = {
  catalog(): Promise<Catalog>;
  feedback: { load(): Promise<Feedback>; save(fb: Feedback): Promise<{ saved?: boolean; smoke?: boolean; items: number }> };
  menuFeedback: { load(): Promise<MenuFeedback>; op(op: MenuOp): Promise<MenuOpResult> };
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
