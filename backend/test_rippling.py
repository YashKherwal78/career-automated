from src.discovery.connectors.rippling import RipplingConnector

connector = RipplingConnector()
print(connector._extract_slug("https://ats.rippling.com/11fs-group-ltd/jobs"))
