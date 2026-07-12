with open("src/discovery/providers/google_dorking.py", "r") as f:
    content = f.read()

new_method = """    async def search_company(self, company_name: str) -> List[str]:
        return await self.fetch_dork(f'site:myworkdayjobs.com "{company_name}"', pages=1)
"""

# Insert right after fetch_dork
content = content.replace("        return urls\n        \n    async def discover_companies", "        return urls\n\n" + new_method + "\n    async def discover_companies")

with open("src/discovery/providers/google_dorking.py", "w") as f:
    f.write(content)
