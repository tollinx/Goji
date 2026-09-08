/**
 * Display copy for the menu page.
 *
 * This is deliberately not the recipe data. Full recipes (ingredients, steps,
 * measurements) live in backend/mcp_server/data/drinks.json, which is the
 * corpus the MCP server retrieves from and the single source of truth. Keeping
 * this file to just what the menu renders means adding a drink touches these
 * few lines plus that JSON, rather than two full recipe definitions.
 */

export interface Drink {
  id: string;
  name: string;
  /** One line under the drink name. */
  note: string;
  /** Handwritten aside in the right-hand column. */
  tagline: string;
}

export const DRINKS: Drink[] = [
  {
    id: 'spiked-goji-tea',
    name: 'Spiked Goji Tea',
    note: 'Warm herbal base with red date and longan doing hot toddy work.',
    tagline: 'the easy one',
  },
  {
    id: 'roasted-oolong-highball',
    name: 'Roasted Oolong Highball',
    note: 'Overnight cold brew avoids the bitterness of a hot steep.',
    tagline: 'not a novelty',
  },
  {
    id: 'osmanthus-gin-sour',
    name: 'Osmanthus Gin Sour',
    note: 'Floral syrup used as both a cocktail modifier and a finishing note.',
    tagline: 'the pretty one',
  },
  {
    id: 'suanmeitang-mezcal',
    name: 'Suanmeitang, Smoke on Smoke',
    note: 'Smoky, tart, dark. Simmered long, then finished with osmanthus.',
    tagline: "nobody's had this",
  },
];
