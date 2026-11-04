export const FRENCH_LEVELS = ['a1', 'a2', 'b1', 'b2', 'c1', 'c2'] as const;

export type FrenchLevel = (typeof FRENCH_LEVELS)[number];

export function isFrenchLevel(value: unknown): value is FrenchLevel {
  return typeof value === 'string' && FRENCH_LEVELS.some((level) => level === value);
}
