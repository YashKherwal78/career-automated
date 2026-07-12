from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re

def canonicalize_url(url: str) -> str:
    """
    Normalizes a candidate URL to prevent duplicates:
    - Lowercase hostname
    - Remove trailing slash
    - Remove default ports
    - Normalize http/https
    - Remove tracking parameters (utm_*, etc.)
    - Normalize duplicate path separators
    - Normalize www.
    """
    try:
        if not url.startswith('http'):
            url = 'https://' + url

        parsed = urlparse(url)
        
        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove default ports
        if scheme == 'http' and netloc.endswith(':80'):
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc.endswith(':443'):
            netloc = netloc[:-4]
            
        # Normalize www.
        if netloc.startswith('www.'):
            netloc = netloc[4:]
            
        # Normalize http to https
        scheme = 'https'
            
        # Normalize duplicate path separators
        path = re.sub(r'//+', '/', parsed.path)
        
        # Remove trailing slash
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
            
        # Remove tracking parameters
        if parsed.query:
            query_params = parse_qsl(parsed.query, keep_blank_values=True)
            filtered_params = [(k, v) for k, v in query_params if not k.lower().startswith('utm_') and k.lower() not in ('ref', 'source', 'gh_src')]
            filtered_params.sort()
            query = urlencode(filtered_params)
        else:
            query = ''
            
        canonical_parsed = parsed._replace(
            scheme=scheme,
            netloc=netloc,
            path=path,
            query=query,
            fragment=''
        )
        
        return urlunparse(canonical_parsed)
    except Exception:
        return url
