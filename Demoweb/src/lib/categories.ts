export const CATEGORIES = ["공지", "스케줄", "사진"] as const;
export type Category = (typeof CATEGORIES)[number];

export const DEFAULT_CATEGORY: Category = "스케줄";

export function isCategory(value: string): value is Category {
  return (CATEGORIES as readonly string[]).includes(value);
}
