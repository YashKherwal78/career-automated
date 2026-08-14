// Client-side prefix trie for instant search-box autocomplete -- avoids a
// network round-trip per keystroke. Built once from a small distinct-title
// list fetched from /jobs/title-suggestions, then queried locally on every
// keystroke (O(prefix length), not O(titles)).

class TrieNode {
  children: Map<string, TrieNode> = new Map();
  titles: Set<string> = new Set();
}

export class Trie {
  private root = new TrieNode();

  insert(title: string): void {
    const normalized = title.toLowerCase();
    let node = this.root;
    for (const ch of normalized) {
      let next = node.children.get(ch);
      if (!next) {
        next = new TrieNode();
        node.children.set(ch, next);
      }
      node = next;
      // Cap how many original titles are tracked per prefix node so a
      // single very common prefix (e.g. "s") doesn't hold references to
      // thousands of titles -- only the first N inserted survive there,
      // which is fine since insertion order is frequency-sorted.
      if (node.titles.size < 50) node.titles.add(title);
    }
  }

  static fromTitles(titles: string[]): Trie {
    const trie = new Trie();
    for (const t of titles) trie.insert(t);
    return trie;
  }

  /** Up to `limit` original-case titles whose lowercase form starts with `prefix`. */
  suggest(prefix: string, limit = 8): string[] {
    const normalized = prefix.toLowerCase();
    if (!normalized) return [];
    let node = this.root;
    for (const ch of normalized) {
      const next = node.children.get(ch);
      if (!next) return [];
      node = next;
    }
    return Array.from(node.titles).slice(0, limit);
  }
}
