import unittest
from src.discovery.pipeline.parsers import WorkdayParser

class TestWorkdayParser(unittest.TestCase):
    def setUp(self):
        self.parser = WorkdayParser()
        
    def test_pattern_a(self):
        identity, conf, reason = self.parser.parse("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")
        self.assertEqual(identity.tenant, "nvidia")
        self.assertEqual(identity.site, "NVIDIAExternalCareerSite")
        self.assertEqual(conf, 0.95)
        
    def test_pattern_a_with_locale(self):
        # /en-US/ locale
        identity, conf, reason = self.parser.parse("https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite")
        self.assertEqual(identity.tenant, "nvidia")
        self.assertEqual(identity.site, "NVIDIAExternalCareerSite")

    def test_pattern_a_with_other_locales(self):
        # /fr-FR/ and /en-GB/
        identity, conf, reason = self.parser.parse("https://nvidia.wd5.myworkdayjobs.com/fr-FR/NVIDIAExternalCareerSite")
        self.assertEqual(identity.tenant, "nvidia")
        self.assertEqual(identity.site, "NVIDIAExternalCareerSite")

        identity, conf, reason = self.parser.parse("https://nvidia.wd5.myworkdayjobs.com/en-GB/NVIDIAExternalCareerSite")
        self.assertEqual(identity.tenant, "nvidia")
        self.assertEqual(identity.site, "NVIDIAExternalCareerSite")

    def test_query_strings_and_fragments(self):
        identity, conf, reason = self.parser.parse("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite?jobFamilyGroup=123#page=2")
        self.assertEqual(identity.tenant, "nvidia")
        self.assertEqual(identity.site, "NVIDIAExternalCareerSite")
        
    def test_trailing_slashes(self):
        identity, conf, reason = self.parser.parse("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/")
        self.assertEqual(identity.tenant, "nvidia")
        self.assertEqual(identity.site, "NVIDIAExternalCareerSite")
        
    def test_pattern_b_recruiting(self):
        identity, conf, reason = self.parser.parse("https://wd3.myworkdayjobs.com/recruiting/stripe/stripe-careers")
        self.assertEqual(identity.tenant, "stripe")
        self.assertEqual(identity.site, "stripe-careers")
        self.assertEqual(conf, 1.0)
        
    def test_pattern_c_apply(self):
        identity, conf, reason = self.parser.parse("https://apply.workday.com/workday/ExternalCareerSite")
        self.assertEqual(identity.tenant, "workday")
        self.assertEqual(identity.site, "ExternalCareerSite")
        self.assertEqual(conf, 0.9)
        
    def test_invalid_domain(self):
        identity, conf, reason = self.parser.parse("https://nvidia.com/careers")
        self.assertIsNone(identity)
        self.assertIn("Not a recognized Workday domain", reason)

if __name__ == '__main__':
    unittest.main()
