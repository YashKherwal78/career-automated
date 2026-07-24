from typing import List, Tuple, Any

class TrieMatcher:
    def __init__(self):
        self.trie = {}

    def add_keyword(self, keyword: str, value: Any):
        """Adds a keyword to the Trie for O(len(text)) matching."""
        if not keyword:
            return
        node = self.trie
        for char in keyword.lower():
            if char not in node:
                node[char] = {}
            node = node[char]
        node['_val'] = value

    def search_all(self, text: str) -> List[Tuple[int, int, Any]]:
        """Scans the text in a single pass to find all keyword matches with boundaries."""
        matches = []
        text_lower = text.lower()
        n = len(text_lower)
        i = 0
        while i < n:
            # Match boundary rule: must not start in the middle of an alphanumeric word
            if i > 0 and text_lower[i-1].isalnum() and text_lower[i-1] not in ['+', '#']:
                i += 1
                continue
                
            node = self.trie
            longest_match = None
            j = i
            while j < n:
                char = text_lower[j]
                if char not in node:
                    break
                node = node[char]
                if '_val' in node:
                    # Boundary rule: check character immediately following match
                    if j == n - 1 or not text_lower[j+1].isalnum() or text_lower[j+1] in ['+', '#']:
                        longest_match = (i, j + 1, node['_val'])
                j += 1
                
            if longest_match:
                matches.append(longest_match)
                i = longest_match[1] # Jump forward
            else:
                i += 1
        return matches
