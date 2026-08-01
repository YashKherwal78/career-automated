import pytest
import asyncio
from src.discovery.connectors.bootstrap import bootstrap_connectors
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.ats_detector import DetectorRegistry
from src.discovery.plugins.indian_ecosystem import StartupIndiaPlugin
from src.discovery.plugins.global_ecosystem import YCombinatorPlugin

def test_indian_ats_connectors_registered():
    bootstrap_connectors()
    providers = list(ConnectorRegistry._registry.keys())
    for p in ['darwinbox', 'freshteam', 'keka', 'zoho_recruit']:
        assert p in providers, f"Provider {p} must be registered in ConnectorRegistry"

def test_ats_detectors_registered():
    detector_ids = [d.provider_id for d in DetectorRegistry._detectors]
    for p in ['darwinbox', 'freshteam', 'keka', 'zoho_recruit']:
        assert p in detector_ids, f"ATS detector for {p} must be registered"

@pytest.mark.asyncio
async def test_discovery_plugins():
    p1 = StartupIndiaPlugin()
    res1 = await p1.discover()
    assert len(res1) > 0
    assert res1[0].source == "StartupIndia"

    p2 = YCombinatorPlugin()
    res2 = await p2.discover()
    assert len(res2) > 0
    assert res2[0].source == "YCombinator"
