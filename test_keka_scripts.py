import urllib.request
import ssl
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == "script":
            for attr in attrs:
                if attr[0] == "src":
                    print("Found Script:", attr[1])

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://awfis.keka.com/careers"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        html = response.read().decode()
        parser = MyHTMLParser()
        parser.feed(html)
except Exception as e:
    print(f"Error: {e}")
