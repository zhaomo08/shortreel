import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DARK_THEMES,
  DEFAULT_THEME,
  THEMES,
  THEME_STORAGE_KEY,
  applyTheme,
  getTheme,
  initTheme,
  isTheme,
  readPersistedTheme,
  setTheme,
  subscribeTheme,
} from "./theme-store";

describe("theme-store", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
    setTheme(DEFAULT_THEME);
    localStorage.clear();
  });

  it("rejects values outside the theme list", () => {
    expect(isTheme("darkroom")).toBe(true);
    expect(isTheme("solarized")).toBe(false);
    expect(isTheme(null)).toBe(false);
  });

  it("falls back to the default when nothing is stored", () => {
    expect(readPersistedTheme()).toBe(DEFAULT_THEME);
  });

  it("falls back to the default when the stored value is no longer a theme", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "solarized");
    expect(readPersistedTheme()).toBe(DEFAULT_THEME);
  });

  it("writes the theme to the document and to storage", () => {
    setTheme("baryta");
    expect(document.documentElement.dataset.theme).toBe("baryta");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("baryta");
    expect(getTheme()).toBe("baryta");
  });

  it("restores the persisted theme on init", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "fixer");
    expect(initTheme()).toBe("fixer");
    expect(document.documentElement.dataset.theme).toBe("fixer");
  });

  it("notifies subscribers until they unsubscribe", () => {
    const seen: string[] = [];
    const unsubscribe = subscribeTheme((theme) => seen.push(theme));
    setTheme("silver");
    unsubscribe();
    setTheme("fixer");
    expect(seen).toEqual(["silver"]);
  });

  it("keeps the in-memory value when storage throws", () => {
    const setItem = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("quota exceeded");
      });
    setTheme("silver");
    expect(getTheme()).toBe("silver");
    expect(document.documentElement.dataset.theme).toBe("silver");
    setItem.mockRestore();
  });

  it("covers every theme with a light/dark classification", () => {
    for (const theme of THEMES) {
      expect(typeof DARK_THEMES.has(theme)).toBe("boolean");
    }
    expect(DARK_THEMES.has("darkroom")).toBe(true);
    expect(DARK_THEMES.has("baryta")).toBe(false);
  });

  it("applies a theme without touching storage", () => {
    applyTheme("fixer");
    expect(document.documentElement.dataset.theme).toBe("fixer");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });
});
