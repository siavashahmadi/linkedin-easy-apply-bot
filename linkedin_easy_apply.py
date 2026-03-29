#!/usr/bin/env python3
r"""
LinkedIn Easy Apply Automation Script
Connects to an existing Chrome session and applies to jobs via Easy Apply.

Usage:
  1. Close Chrome completely
  2. Relaunch Chrome with:
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  3. Log into LinkedIn in that Chrome window
  4. Run: python3 linkedin_easy_apply.py
"""

import time
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)

# ─── CONFIG ───────────────────────────────────────────────────────────
CONFIG = {
    "search_keywords": '(frontend OR fullstack OR "full stack" OR "web developer" OR devops OR "cloud engineer" OR "platform engineer") AND (react OR node OR python OR AWS OR angular OR typescript)',
    "location": "New York City",
    "experience_levels": "2,3,4",  # 2=Entry, 3=Associate, 4=Mid-Senior
    "job_type": "F",               # F=Full-time
    "work_type": "",               # 1=On-site, 2=Remote, 3=Hybrid (empty=all)
    "time_posted": "r86400",       # r86400=24h, r604800=week, r2592000=month
    "max_applications": 50,        # LinkedIn daily Easy Apply limit is ~50
    "min_delay": 2,
    "max_delay": 5,
    "page_load_wait": 10,
    "chrome_debug_port": 9222,
}

# ─── LOGGING ──────────────────────────────────────────────────────────
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"linkedin_apply_{timestamp}.log"),
    ],
)
log = logging.getLogger(__name__)

# ─── STATS ────────────────────────────────────────────────────────────
stats = {"applied": 0, "skipped": 0, "failed": 0, "companies": []}


def random_delay(min_s=None, max_s=None):
    """Sleep for a random duration to mimic human behavior."""
    lo = min_s or CONFIG["min_delay"]
    hi = max_s or CONFIG["max_delay"]
    time.sleep(random.uniform(lo, hi))


def connect_to_chrome():
    """Attach Selenium to an already-running Chrome with remote debugging."""
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{CONFIG['chrome_debug_port']}")
    driver = webdriver.Chrome(options=opts)
    log.info("Connected to Chrome session")
    return driver


def wait_and_click(driver, by, value, timeout=10, description="element"):
    """Wait for an element to be clickable, then click it."""
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.5)
        el.click()
        log.debug(f"Clicked: {description}")
        return True
    except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
        log.warning(f"Could not click {description}: {e.__class__.__name__}")
        return False


def wait_and_find(driver, by, value, timeout=10):
    """Wait for an element to be present and return it."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def safe_find_elements(driver, by, value):
    """Find elements without throwing if none found."""
    try:
        return driver.find_elements(by, value)
    except Exception:
        return []


def navigate_to_search(driver):
    """Open LinkedIn job search with Easy Apply + Most Recent filters."""
    from urllib.parse import quote
    url = (
        "https://www.linkedin.com/jobs/search/?"
        f"keywords={quote(CONFIG['search_keywords'])}"
        f"&location={quote(CONFIG['location'])}"
        "&f_EA=true"   # Easy Apply (NOT f_AL which is "Actively Hiring")
        "&sortBy=DD"   # Most Recent
    )
    if CONFIG.get("experience_levels"):
        url += f"&f_E={CONFIG['experience_levels'].replace(',', '%2C')}"
    if CONFIG.get("job_type"):
        url += f"&f_JT={CONFIG['job_type']}"
    if CONFIG.get("work_type"):
        url += f"&f_WT={CONFIG['work_type'].replace(',', '%2C')}"
    if CONFIG.get("time_posted"):
        url += f"&f_TPR={CONFIG['time_posted']}"
    driver.get(url)
    log.info(f"Navigated to job search: {CONFIG['search_keywords']}")
    random_delay(3, 5)


def get_job_cards(driver):
    """Return all visible job cards in the left panel."""
    return safe_find_elements(
        driver, By.CSS_SELECTOR,
        ".jobs-search-results__list-item, .scaffold-layout__list-item"
    )


def is_already_applied(driver):
    """Check if the job detail panel shows 'Applied'."""
    indicators = safe_find_elements(
        driver, By.CSS_SELECTOR,
        ".jobs-s-apply .artdeco-inline-feedback, span.artdeco-inline-feedback__message"
    )
    for el in indicators:
        if "applied" in el.text.lower():
            return True
    # Also check for "Applied" badge text
    badges = safe_find_elements(driver, By.CSS_SELECTOR, ".jobs-details__main-content .t-bold")
    for b in badges:
        if "applied" in b.text.lower():
            return True
    return False


def click_easy_apply(driver):
    """Click the Easy Apply button on the job detail pane."""
    result = driver.execute_script("""
        // Target the actual apply button — NOT the filter pill at the top
        var btn = document.querySelector('button.jobs-apply-button')
               || document.getElementById('jobs-apply-button-id');
        if (btn && btn.offsetParent !== null) {
            btn.scrollIntoView({block: 'center'});
            btn.click();
            return true;
        }
        // Fallback: artdeco-button (not pill) with "Easy Apply" text
        var buttons = document.querySelectorAll('button.artdeco-button');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].classList.contains('artdeco-pill')) continue;
            var text = buttons[i].textContent.trim().toLowerCase();
            if (text.includes('easy apply') && buttons[i].offsetParent !== null) {
                buttons[i].scrollIntoView({block: 'center'});
                buttons[i].click();
                return true;
            }
        }
        return false;
    """)
    if result:
        log.info("  Clicked Easy Apply button")
        # Wait for the modal to fully load
        for _ in range(10):
            time.sleep(0.5)
            modal_ready = driver.execute_script("""
                var modal = document.querySelector('.artdeco-modal');
                if (!modal) return false;
                var primary = modal.querySelector('button.artdeco-button--primary');
                return primary !== null && primary.offsetParent !== null;
            """)
            if modal_ready:
                log.debug("  Modal is ready")
                return True
        log.warning("  Modal did not load in time")
        return True  # Still return True — maybe it's a different layout
    return False


def fill_text_inputs(driver):
    """Fill any empty text/number inputs in the form with '1'."""
    inputs = safe_find_elements(driver, By.CSS_SELECTOR,
        "input[type='text'], input[type='number'], input[type='tel']")
    for inp in inputs:
        try:
            if not inp.get_attribute("value") and inp.is_displayed():
                label_text = ""
                # Try to find associated label
                inp_id = inp.get_attribute("id")
                if inp_id:
                    labels = safe_find_elements(driver, By.CSS_SELECTOR, f"label[for='{inp_id}']")
                    if labels:
                        label_text = labels[0].text

                # Skip phone/email/name fields (already filled)
                skip_keywords = ["phone", "email", "name", "first", "last", "city", "address"]
                if any(kw in label_text.lower() for kw in skip_keywords):
                    continue

                inp.clear()
                inp.send_keys("1")
                log.debug(f"Filled input '{label_text}' with '1'")
        except Exception:
            continue


def fill_dropdowns(driver):
    """Handle select dropdowns — pick 'Yes' if available, otherwise first real option."""
    # Native <select> elements
    selects = safe_find_elements(driver, By.CSS_SELECTOR, "select")
    for sel in selects:
        try:
            if not sel.is_displayed():
                continue
            options = sel.find_elements(By.TAG_NAME, "option")
            # Check if already has a non-default value
            selected_opt = [o for o in options if o.is_selected()]
            if selected_opt and selected_opt[0].text.strip().lower() not in ("select an option", "select", "", "--"):
                continue

            # Try to pick "Yes" first
            for opt in options:
                if opt.text.strip().lower() == "yes":
                    opt.click()
                    log.debug("Selected 'Yes' in native dropdown")
                    break
            else:
                for opt in options:
                    val = opt.text.strip().lower()
                    if val and val not in ("select an option", "select", "", "--"):
                        opt.click()
                        log.debug(f"Selected '{opt.text}' in native dropdown")
                        break
        except Exception:
            continue

    # LinkedIn also uses custom dropdowns with data-test attributes
    # These show "Select an option" and need to be clicked to expand
    try:
        custom_selects = driver.execute_script("""
            var results = [];
            var selects = document.querySelectorAll('select');
            selects.forEach(function(s) {
                if (s.offsetParent !== null) {  // visible
                    var val = s.value;
                    var text = s.options[s.selectedIndex] ? s.options[s.selectedIndex].text : '';
                    if (!val || text.toLowerCase().includes('select')) {
                        results.push(s);
                    }
                }
            });
            return results;
        """)
        for sel in (custom_selects or []):
            try:
                options = sel.find_elements(By.TAG_NAME, "option")
                for opt in options:
                    if opt.text.strip().lower() == "yes":
                        driver.execute_script("arguments[0].selected = true; arguments[1].dispatchEvent(new Event('change'));", opt, sel)
                        log.debug("Selected 'Yes' via JS dispatch")
                        break
                else:
                    for opt in options:
                        val = opt.text.strip().lower()
                        if val and val not in ("select an option", "select", "", "--"):
                            driver.execute_script("arguments[0].selected = true; arguments[1].dispatchEvent(new Event('change'));", opt, sel)
                            log.debug(f"Selected '{opt.text}' via JS dispatch")
                            break
            except Exception:
                continue
    except Exception:
        pass


def fill_radio_buttons(driver):
    """Select 'Yes' for radio button groups, or first option if no 'Yes'."""
    fieldsets = safe_find_elements(driver, By.CSS_SELECTOR, "fieldset")
    for fieldset in fieldsets:
        try:
            radios = fieldset.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            if not radios:
                continue

            # Check if any is already selected
            already_selected = any(r.is_selected() for r in radios)
            if already_selected:
                continue

            # Try to find and click "Yes"
            labels = fieldset.find_elements(By.CSS_SELECTOR, "label")
            clicked = False
            for label in labels:
                if label.text.strip().lower() == "yes":
                    label.click()
                    clicked = True
                    log.debug("Selected 'Yes' radio button")
                    break

            if not clicked and labels:
                labels[0].click()
                log.debug(f"Selected first radio option: {labels[0].text}")
        except Exception:
            continue


def check_checkboxes(driver):
    """Check any unchecked T&C or agreement checkboxes (except Follow)."""
    checkboxes = safe_find_elements(driver, By.CSS_SELECTOR, "input[type='checkbox']")
    for cb in checkboxes:
        try:
            if not cb.is_displayed():
                continue

            # Find the label
            label_text = ""
            cb_id = cb.get_attribute("id")
            if cb_id:
                labels = safe_find_elements(driver, By.CSS_SELECTOR, f"label[for='{cb_id}']")
                if labels:
                    label_text = labels[0].text.lower()

            # Check T&C / agreement boxes
            if any(kw in label_text for kw in ["agree", "terms", "conditions", "acknowledge"]):
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
                    log.debug(f"Checked agreement checkbox: {label_text[:50]}")
        except Exception:
            continue


def uncheck_follow(driver):
    """Uncheck the 'Follow [company]' checkbox inside the modal."""
    result = driver.execute_script("""
        var modal = document.querySelector('.artdeco-modal');
        if (!modal) return 'no modal';

        // Find all labels in the modal that mention "Follow" and "stay up to date"
        var labels = modal.querySelectorAll('label');
        for (var i = 0; i < labels.length; i++) {
            var text = labels[i].textContent.toLowerCase();
            if (text.includes('follow') && text.includes('stay up to date')) {
                // Find the associated checkbox
                var forId = labels[i].getAttribute('for');
                var checkbox = forId ? document.getElementById(forId) : null;
                if (!checkbox) {
                    // Try finding checkbox as sibling
                    var parent = labels[i].parentElement;
                    checkbox = parent ? parent.querySelector('input[type="checkbox"]') : null;
                }
                if (checkbox && checkbox.checked) {
                    checkbox.click();
                    return 'unchecked';
                } else if (checkbox && !checkbox.checked) {
                    return 'already unchecked';
                }
            }
        }

        // Fallback: find any checkbox near "Follow" text
        var checkboxes = modal.querySelectorAll('input[type="checkbox"]');
        for (var i = 0; i < checkboxes.length; i++) {
            var parent = checkboxes[i].closest('div, label, span');
            if (parent && parent.textContent.toLowerCase().includes('follow')) {
                if (checkboxes[i].checked) {
                    checkboxes[i].click();
                    return 'unchecked (fallback)';
                }
            }
        }
        return 'not found';
    """)
    log.info(f"  Follow checkbox: {result}")


def fill_textarea(driver):
    """Fill any empty textareas with a brief response."""
    textareas = safe_find_elements(driver, By.CSS_SELECTOR, "textarea")
    for ta in textareas:
        try:
            if not ta.get_attribute("value") and ta.is_displayed():
                label_text = ""
                ta_id = ta.get_attribute("id")
                if ta_id:
                    labels = safe_find_elements(driver, By.CSS_SELECTOR, f"label[for='{ta_id}']")
                    if labels:
                        label_text = labels[0].text.lower()

                if "experience" in label_text or "relevant" in label_text:
                    ta.send_keys(
                        "5+ years of software engineering experience with full-stack "
                        "development using Java, Python, React, and cloud services (AWS, GCP)."
                    )
                else:
                    ta.send_keys("N/A")
                log.debug(f"Filled textarea: {label_text[:50]}")
        except Exception:
            continue


def handle_form_page(driver):
    """Process all form fields on the current page."""
    random_delay(1, 2)
    fill_text_inputs(driver)
    fill_dropdowns(driver)
    fill_radio_buttons(driver)
    check_checkboxes(driver)
    fill_textarea(driver)


def is_review_page(driver):
    """Check if we're on the review/submit page."""
    try:
        result = driver.execute_script("""
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent.trim().toLowerCase();
                if (text.includes('submit application')) return true;
            }
            // Also check for "Review your application" heading
            var headings = document.querySelectorAll('h3, h2, .t-16');
            for (var i = 0; i < headings.length; i++) {
                if (headings[i].textContent.toLowerCase().includes('review')) return true;
            }
            return false;
        """)
        return result
    except Exception:
        return False


def click_next_or_review(driver):
    """Click Next, Review, or Submit button in the Easy Apply modal.

    LinkedIn's modal always uses button.artdeco-button--primary inside
    .artdeco-modal for the main action (Next / Review / Submit application).
    """
    # The primary action button is ALWAYS: .artdeco-modal button.artdeco-button--primary
    # Its text is "Next", "Review", or "Submit application"
    result = driver.execute_script("""
        var modal = document.querySelector('.artdeco-modal');
        if (!modal) return null;

        // Find the primary button inside the modal
        var primary = modal.querySelector('button.artdeco-button--primary');
        if (primary && primary.offsetParent !== null) {
            var text = primary.textContent.trim().toLowerCase();
            primary.scrollIntoView({block: 'center'});
            primary.click();
            return text;
        }

        // Fallback: find any button with Submit/Review/Next text
        var buttons = modal.querySelectorAll('button');
        var targets = ['submit application', 'review', 'next'];
        for (var t = 0; t < targets.length; t++) {
            for (var i = 0; i < buttons.length; i++) {
                var btnText = buttons[i].textContent.trim().toLowerCase();
                if (btnText.includes(targets[t]) && buttons[i].offsetParent !== null) {
                    buttons[i].scrollIntoView({block: 'center'});
                    buttons[i].click();
                    return btnText;
                }
            }
        }
        return null;
    """)

    if result:
        log.info(f"  Clicked modal button: '{result}'")
        return result

    # Debug: log what buttons we CAN see
    try:
        debug_info = driver.execute_script("""
            var modal = document.querySelector('.artdeco-modal');
            if (!modal) return 'NO MODAL FOUND';
            var buttons = modal.querySelectorAll('button');
            var visible = [];
            buttons.forEach(function(b) {
                if (b.offsetParent !== null && b.textContent.trim()) {
                    visible.push(b.textContent.trim().substring(0, 40) + ' [' + b.className.substring(0, 50) + ']');
                }
            });
            return visible.join(' | ');
        """)
        log.warning(f"  No action button found. Modal buttons: {debug_info}")
    except Exception:
        log.warning("  No action button found and debug failed")

    return None


def dismiss_post_apply(driver):
    """Dismiss the post-apply modal (click 'Not now' or close)."""
    random_delay(1, 2)
    driver.execute_script("""
        // Try "Not now" button first
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.trim().toLowerCase().includes('not now')) {
                buttons[i].click();
                return;
            }
        }
        // Try dismiss/close button
        var dismiss = document.querySelector('button[aria-label="Dismiss"]')
                   || document.querySelector('.artdeco-modal__dismiss');
        if (dismiss) dismiss.click();
    """)
    log.debug("  Dismissed post-apply modal")


def process_application(driver):
    """Navigate through the entire Easy Apply flow for one job."""
    max_pages = 12  # Safety limit

    for page_num in range(max_pages):
        random_delay(1, 2)

        # Check if modal is still open
        modal_open = driver.execute_script("""
            return document.querySelector('.artdeco-modal--is-open') !== null ||
                   document.querySelector('.jobs-easy-apply-modal') !== null ||
                   document.querySelector('[data-test-modal]') !== null;
        """)
        if not modal_open:
            # Check if we landed on a post-apply page (success!)
            if "post-apply" in driver.current_url:
                log.info("  Application submitted (detected via URL)")
                dismiss_post_apply(driver)
                return True
            log.debug("  Modal closed unexpectedly")
            return False

        # Fill the current page
        handle_form_page(driver)

        # Check if this is the review/submit page
        if is_review_page(driver):
            uncheck_follow(driver)
            random_delay(0.5, 1)
            clicked = click_next_or_review(driver)
            if clicked and "submit" in (clicked or ""):
                log.info("  Submitted application!")
                random_delay(2, 3)
                dismiss_post_apply(driver)
                return True
            elif clicked:
                # Clicked something (review?) — continue to next iteration
                random_delay(1, 2)
                continue
        else:
            # Not review page — click Next
            clicked = click_next_or_review(driver)
            if not clicked:
                log.warning("  No Next/Review/Submit button found on page " + str(page_num + 1))
                return False

        random_delay(1, 2)

    log.warning("  Exceeded max pages — aborting this application")
    return False


def close_modal(driver):
    """Close any open Easy Apply modal and handle discard confirmation."""
    try:
        # Click the X/dismiss button
        driver.execute_script("""
            var dismiss = document.querySelector('button[aria-label="Dismiss"]')
                       || document.querySelector('.artdeco-modal__dismiss');
            if (dismiss) dismiss.click();
        """)
        time.sleep(1.5)

        # Handle "Discard" confirmation dialog
        driver.execute_script("""
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent.trim().toLowerCase();
                if (text.includes('discard')) {
                    buttons[i].click();
                    return;
                }
            }
        """)
        time.sleep(0.5)
    except Exception:
        pass


def main():
    log.info("=" * 60)
    log.info("LinkedIn Easy Apply Automation")
    log.info(f"Target: {CONFIG['max_applications']} applications")
    log.info("=" * 60)

    driver = connect_to_chrome()
    navigate_to_search(driver)

    page = 1

    while stats["applied"] < CONFIG["max_applications"]:
        log.info(f"--- Page {page} | Applied: {stats['applied']} ---")
        random_delay(2, 4)

        # Count job cards once
        num_cards = len(get_job_cards(driver))
        if num_cards == 0:
            log.warning("No job cards found on this page")
            break

        log.info(f"Found {num_cards} job cards")

        for idx in range(num_cards):
            if stats["applied"] >= CONFIG["max_applications"]:
                break

            try:
                # Re-fetch the card by index each time to avoid stale references
                cards = get_job_cards(driver)
                if idx >= len(cards):
                    log.debug(f"  Card index {idx} out of range, skipping")
                    break
                card = cards[idx]

                # Click the job card's link to load it in the detail pane
                driver.execute_script("""
                    var cards = document.querySelectorAll(
                        '.jobs-search-results__list-item, .scaffold-layout__list-item'
                    );
                    if (arguments[0] < cards.length) {
                        var card = cards[arguments[0]];
                        var link = card.querySelector('a.job-card-container__link')
                                || card.querySelector('a[href*="/jobs/view/"]')
                                || card.querySelector('a');
                        var target = link || card;
                        target.scrollIntoView({block: 'center'});
                        target.click();
                    }
                """, idx)
                random_delay(2, 4)

                # Get job title
                try:
                    job_title = driver.execute_script("""
                        var el = document.querySelector(
                            '.jobs-details__main-content h1, ' +
                            '.job-details-jobs-unified-top-card__job-title, ' +
                            'h1.t-24, h2.t-24'
                        );
                        return el ? el.textContent.trim() : null;
                    """) or f"Job #{idx + 1}"
                except Exception:
                    job_title = f"Job #{idx + 1}"

                log.info(f"Processing: {job_title}")

                # Check if already applied
                if is_already_applied(driver):
                    log.info(f"  → Already applied, skipping")
                    stats["skipped"] += 1
                    continue

                # Click Easy Apply
                if not click_easy_apply(driver):
                    log.info(f"  → No Easy Apply button, skipping")
                    stats["skipped"] += 1
                    continue

                # Process the application
                success = process_application(driver)

                if success:
                    stats["applied"] += 1
                    stats["companies"].append(job_title)
                    log.info(f"  ✓ Application #{stats['applied']} submitted: {job_title}")
                else:
                    stats["failed"] += 1
                    log.warning(f"  ✗ Failed to apply: {job_title}")
                    close_modal(driver)

                random_delay()

            except Exception as e:
                log.error(f"  Error processing job #{idx}: {e}")
                stats["failed"] += 1
                close_modal(driver)
                random_delay()

        # Go to next page
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR,
                "button[aria-label='View next page'], li.artdeco-pagination__indicator--number.active + li button")
            next_btn.click()
            page += 1
            random_delay(3, 5)
        except Exception:
            log.info("No more pages available")
            break

    # Summary
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info(f"  Applied:  {stats['applied']}")
    log.info(f"  Skipped:  {stats['skipped']}")
    log.info(f"  Failed:   {stats['failed']}")
    log.info("Companies applied to:")
    for company in stats["companies"]:
        log.info(f"  • {company}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
