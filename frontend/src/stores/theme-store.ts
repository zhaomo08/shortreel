/**
 * 配色主题：值写在 <html data-theme>，取值由 index.css 的 :root[data-theme] 块给出。
 *
 * 主题只改自定义属性的取值，不改类名，所以切换不触发任何组件重渲染——写 DOM 属性
 * 即可生效。store 仍持有当前值，供设置页回显选中态。
 */

export const THEMES = ["darkroom", "fixer", "baryta", "silver"] as const;
export type Theme = (typeof THEMES)[number];

export const DEFAULT_THEME: Theme = "darkroom";

/** 深色主题集合——供需要按明暗分组呈现的界面使用。 */
export const DARK_THEMES: ReadonlySet<Theme> = new Set<Theme>(["darkroom", "fixer"]);

export const THEME_STORAGE_KEY = "arcreel.theme";

export function isTheme(value: unknown): value is Theme {
  return typeof value === "string" && (THEMES as readonly string[]).includes(value);
}

export function readPersistedTheme(): Theme {
  if (typeof window === "undefined") return DEFAULT_THEME;
  try {
    const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(raw) ? raw : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

function persistTheme(theme: Theme): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // localStorage 不可用（隐私模式 / quota exceeded）时仅保留内存值
  }
}

/** 把主题落到 <html data-theme>；:root 默认块已等同 darkroom，故不特判。 */
export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = theme;
}

let current: Theme = DEFAULT_THEME;
const listeners = new Set<(theme: Theme) => void>();

export function getTheme(): Theme {
  return current;
}

export function setTheme(theme: Theme): void {
  current = theme;
  applyTheme(theme);
  persistTheme(theme);
  for (const listener of listeners) listener(theme);
}

export function subscribeTheme(listener: (theme: Theme) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** 应用启动时调用一次：把持久化值读回内存并落到 DOM。 */
export function initTheme(): Theme {
  current = readPersistedTheme();
  applyTheme(current);
  return current;
}
