// Minimal dnd5eapi types we use for pickers
export interface APIRef {
  index: string;
  name: string;
  url: string;
}

export interface APIList<T = APIRef> {
  count: number;
  results: T[];
}
