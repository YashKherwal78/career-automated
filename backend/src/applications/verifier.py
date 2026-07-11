import re
from playwright.sync_api import Page

class SubmissionVerifier:
    @staticmethod
    def verify(page: Page, ats_type: str, active_context=None) -> dict:
        """
        Verifies if an application was successfully submitted using a weighted confidence model.
        Supports checking an active_context (like an iframe) before falling back to the main page.
        """
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except: pass
            
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except: pass

        url = page.url
        title = page.title()
        
        proof = {
            "url": url,
            "title": title,
            "success_text": "",
            "error_text": "",
            "context_used": "main_page",
            "success_signals_found": 0,
            "failure_signals_found": 0
        }
        
        # Helper to check a specific context for signals
        def check_context(ctx, is_iframe=False):
            try:
                # If ctx is a FrameLocator or Frame, inner_text works on locator("body")
                # Wait for any potential reloads in the frame
                ctx.locator("body").wait_for(timeout=3000)
                visible_text = ctx.locator("body").inner_text().lower()
            except:
                visible_text = ""
                
            signals = {"success": [], "failure": [], "text": visible_text}
            
            # Failure Detection
            try:
                error_locators = ctx.locator('.error-message, .field_with_errors, .application-error, [class*="error"]')
                if error_locators.count() > 0:
                    for i in range(error_locators.count()):
                        e = error_locators.nth(i)
                        if e.is_visible():
                            txt = e.inner_text().strip()
                            if len(txt) > 3 and len(txt) < 100:
                                signals["failure"].append(txt)
            except: pass
            
            # Success Detection
            success_phrases = [
                "application submitted",
                "thank you for applying",
                "we've received your application",
                "your application has been received",
                "successfully submitted",
                "application complete",
                "submission received"
            ]
            
            for phrase in success_phrases:
                if phrase in visible_text:
                    signals["success"].append(phrase)
                    
            return signals

        # PRIORITY 1: Active Context (e.g. iframe)
        signals = {"success": [], "failure": [], "text": ""}
        if active_context:
            proof["context_used"] = "iframe"
            signals = check_context(active_context, is_iframe=True)
            
            # If no signals in iframe, fallback to main page
            if not signals["success"] and not signals["failure"]:
                proof["context_used"] = "main_page"
                signals = check_context(page)
        else:
            signals = check_context(page)

        proof["success_signals_found"] = len(signals["success"])
        proof["failure_signals_found"] = len(signals["failure"])

        # Check for CAPTCHA
        title_lower = title.lower()
        if "just a moment" in title_lower or "attention required" in title_lower or "captcha" in title_lower:
            proof["error_text"] = "Captcha or bot protection detected."
            return {"status": "FAILED_UNRECOVERABLE", "proof": proof, "confidence": 100}

        # If failures detected
        if signals["failure"]:
            proof["error_text"] = "Validation errors: " + " | ".join(signals["failure"])
            return {"status": "FAILED_RECOVERABLE", "proof": proof, "confidence": 90}
            
        confidence = 0
        
        # URL / Title heuristics (Outer page)
        if "confirmation" in url.lower() or "success" in url.lower() or "thanks" in url.lower():
            confidence += 40
        if "thank you" in title_lower or "success" in title_lower or "application received" in title_lower:
            confidence += 40
            
        # Body text heuristics
        if signals["success"]:
            confidence += 60
            proof["success_text"] = signals["success"][0]
            
        if ats_type == "GREENHOUSE" and signals["success"]:
            confidence += 30
            
        confidence = min(confidence, 100)
        
        if confidence >= 80:
            status = "SUBMITTED_CONFIRMED"
        elif confidence >= 40:
            status = "REVIEW_REQUIRED"
            proof["error_text"] = f"Ambiguous success (Confidence {confidence})"
        else:
            status = "FAILED_RECOVERABLE"
            proof["error_text"] = "No success signals detected after clicking submit."

        try:
            page.screenshot(path="/Users/yashkherwal/.gemini/antigravity/brain/85072219-ca5f-4b8a-911f-47be32349a8b/images/submission_proof.png")
        except Exception:
            pass

        try:
            page.screenshot(path="/Users/yashkherwal/.gemini/antigravity/brain/85072219-ca5f-4b8a-911f-47be32349a8b/images/submission_proof.png")
        except Exception:
            pass

        return {
            "status": status,
            "proof": proof,
            "confidence": confidence
        }
