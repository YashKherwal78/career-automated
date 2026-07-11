import re
from urllib.parse import urlparse, urlunparse

class URLCanonicalizer:
    @staticmethod
    def canonicalize(url: str) -> str:
        """
        Deduplicates URL variants before scoring.
        Removes tracking params, hash fragments, and normalizes trailing slashes.
        Also normalizes known Workday paths like /en-US/ to standard.
        """
        parsed = urlparse(url)
        
        # Remove tracking params and fragments
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Strip trailing slash
        path = parsed.path.rstrip('/')
        
        # Normalization for Workday URLs
        if 'myworkdayjobs.com' in netloc:
            # Strip standard locale prefixes like /en-US
            path = re.sub(r'^/[a-z]{2}-[A-Z]{2}(?=/|$)', '', path)
            if not path:
                path = '/'
                
        canonical = urlunparse((scheme, netloc, path, '', '', ''))
        return canonical
