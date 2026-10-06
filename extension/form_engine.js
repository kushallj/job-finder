/**
 * extension/form_engine.js
 * 
 * Next.js, React 16-19, and Modern SPA Form Automation Engine.
 * 
 * Solves:
 * 1. React Controlled Inputs & fiber valueTracker traps
 * 2. Custom ARIA Comboboxes / Dropdowns (Radix UI, MUI, Headless UI, Shadcn, React-Select)
 * 3. Radio groups, checkboxes, and boolean logic toggles
 * 4. Semantic field categorization & fuzzy scoring
 * 5. Ghost-fill visual cue & validation triggers
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.FormEngine = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {

  // Native prototype property setters to bypass React / Next.js tracker interception
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    typeof window !== 'undefined' && window.HTMLInputElement ? window.HTMLInputElement.prototype : {},
    'value'
  )?.set;

  const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
    typeof window !== 'undefined' && window.HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : {},
    'value'
  )?.set;

  const nativeSelectValueSetter = Object.getOwnPropertyDescriptor(
    typeof window !== 'undefined' && window.HTMLSelectElement ? window.HTMLSelectElement.prototype : {},
    'value'
  )?.set;

  const nativeCheckboxCheckedSetter = Object.getOwnPropertyDescriptor(
    typeof window !== 'undefined' && window.HTMLInputElement ? window.HTMLInputElement.prototype : {},
    'checked'
  )?.set;

  /**
   * Dispatch full synthetic event sequence to ensure React Hook Form,
   * Formik, Redux, or vanilla handlers register the change.
   */
  function dispatchReactEvents(element) {
    if (!element || typeof element.dispatchEvent !== 'function') return;

    const createEvt = (type, ctorName, options = { bubbles: true }) => {
      try {
        if (typeof window !== 'undefined' && window[ctorName]) {
          return new window[ctorName](type, options);
        }
        if (typeof Event !== 'undefined') {
          return new Event(type, options);
        }
      } catch (_) {}
      return { type, bubbles: true };
    };

    // Focus
    element.dispatchEvent(createEvt('focus', 'FocusEvent'));

    // Input & Change with bubbles
    element.dispatchEvent(createEvt('input', 'Event', { bubbles: true, cancelable: true }));
    element.dispatchEvent(createEvt('change', 'Event', { bubbles: true, cancelable: true }));

    // Key stroke simulations for reactive listeners
    element.dispatchEvent(createEvt('keydown', 'KeyboardEvent', { bubbles: true, key: 'Enter' }));
    element.dispatchEvent(createEvt('keyup', 'KeyboardEvent', { bubbles: true, key: 'Enter' }));

    // Blur to mark touched/dirty in form libraries
    element.dispatchEvent(createEvt('blur', 'FocusEvent'));
  }

  /**
   * Set text on an <input> element safely in React/Next.js
   */
  function setInputValue(input, val) {
    if (!input) return false;
    const stringVal = val === null || val === undefined ? '' : String(val);

    try {
      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(input, stringVal);
      } else {
        input.value = stringVal;
      }
    } catch (_) {
      input.value = stringVal;
    }

    // Assign internal React tracker if present
    const tracker = input._valueTracker;
    if (tracker) {
      tracker.setValue('');
    }

    dispatchReactEvents(input);
    highlightElement(input);
    return true;
  }

  /**
   * Set text on a <textarea> element safely in React/Next.js
   */
  function setTextareaValue(textarea, val) {
    if (!textarea) return false;
    const stringVal = val === null || val === undefined ? '' : String(val);

    try {
      if (nativeTextAreaValueSetter) {
        nativeTextAreaValueSetter.call(textarea, stringVal);
      } else {
        textarea.value = stringVal;
      }
    } catch (_) {
      textarea.value = stringVal;
    }

    const tracker = textarea._valueTracker;
    if (tracker) {
      tracker.setValue('');
    }

    dispatchReactEvents(textarea);
    highlightElement(textarea);
    return true;
  }

  /**
   * Set value on standard <select> dropdown
   */
  function setSelectValue(select, val) {
    if (!select) return false;
    const stringVal = String(val).toLowerCase().trim();

    let matchedOption = null;
    for (const opt of select.options) {
      const optVal = (opt.value || '').toLowerCase().trim();
      const optTxt = (opt.text || '').toLowerCase().trim();
      if (optVal === stringVal || optTxt === stringVal || optTxt.includes(stringVal)) {
        matchedOption = opt;
        break;
      }
    }

    if (matchedOption) {
      if (nativeSelectValueSetter) {
        nativeSelectValueSetter.call(select, matchedOption.value);
      } else {
        select.value = matchedOption.value;
      }
      matchedOption.selected = true;
      dispatchReactEvents(select);
      highlightElement(select);
      return true;
    }
    return false;
  }

  /**
   * Set Checkbox state safely
   */
  function setCheckboxValue(input, boolVal) {
    if (!input) return false;
    const target = Boolean(boolVal);

    if (nativeCheckboxCheckedSetter) {
      nativeCheckboxCheckedSetter.call(input, target);
    } else {
      input.checked = target;
    }

    const tracker = input._valueTracker;
    if (tracker) {
      tracker.setValue(!target ? 'true' : 'false');
    }

    dispatchReactEvents(input);
    highlightElement(input);
    return true;
  }

  /**
   * Select a Radio button inside a radio group
   */
  function selectRadioOption(radioGroup, targetValue) {
    if (!radioGroup || !radioGroup.length) return false;
    const targetStr = String(targetValue).toLowerCase().trim();

    for (const radio of radioGroup) {
      const label = findAssociatedLabel(radio).toLowerCase();
      const val = (radio.value || '').toLowerCase();

      // Check for boolean equivalents (yes/no, true/false)
      const isYes = targetStr === 'true' || targetStr === 'yes' || targetStr === '1';
      const isNo = targetStr === 'false' || targetStr === 'no' || targetStr === '0';

      const radioSaysYes = val.includes('yes') || val === '1' || label.includes('yes');
      const radioSaysNo = val.includes('no') || val === '0' || label.includes('no');

      if ((isYes && radioSaysYes) || (isNo && radioSaysNo) || val.includes(targetStr) || label.includes(targetStr)) {
        radio.click();
        setCheckboxValue(radio, true);
        return true;
      }
    }
    return false;
  }

  /**
   * Custom ARIA Combobox / Virtualized Dropdown clicker
   * (e.g. Radix UI, Shadcn, MUI Autocomplete, React-Select)
   */
  async function selectCustomDropdown(comboboxEl, targetValue) {
    if (!comboboxEl) return false;
    const targetStr = String(targetValue).toLowerCase().trim();

    // 1. Focus and click to open
    comboboxEl.focus();
    comboboxEl.click();
    comboboxEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));

    // If it's an input combobox, type the query
    if (comboboxEl.tagName === 'INPUT') {
      setInputValue(comboboxEl, targetValue);
    }

    // 2. Allow Next.js / React microtask to render the popover / listbox
    await new Promise((r) => setTimeout(r, 120));

    // 3. Search for popup options in document body
    const optionSelectors = [
      '[role="option"]',
      '.select__option',
      '[data-radix-collection-item]',
      '.MuiAutocomplete-option',
      'li[role="option"]',
      'div[role="option"]',
    ];

    const options = Array.from(document.querySelectorAll(optionSelectors.join(','))).filter(
      (el) => el.offsetParent !== null
    );

    for (const opt of options) {
      const txt = (opt.textContent || '').toLowerCase().trim();
      if (txt === targetStr || txt.includes(targetStr)) {
        opt.click();
        opt.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        highlightElement(comboboxEl);
        return true;
      }
    }

    // Fallback: keyboard navigation
    comboboxEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    comboboxEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    return false;
  }

  /**
   * Subtle green pulse indicator on auto-filled elements
   */
  function highlightElement(el) {
    if (!el || !el.style) return;
    const originalTransition = el.style.transition;
    const originalBoxShadow = el.style.boxShadow;
    const originalOutline = el.style.outline;

    el.style.transition = 'all 0.3s ease';
    el.style.outline = '2px solid #10b981';
    el.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.4)';

    setTimeout(() => {
      el.style.outline = originalOutline;
      el.style.boxShadow = originalBoxShadow;
      el.style.transition = originalTransition;
    }, 2500);
  }

  /**
   * Detect common Captcha / Bot Challenge elements on the page
   * (Cloudflare Turnstile, Google reCAPTCHA, Arkose Labs, hCaptcha)
   */
  function detectCaptchaElements(root = document) {
    const captchaSelectors = [
      'iframe[src*="challenges.cloudflare.com"]',
      'iframe[src*="recaptcha"]',
      'iframe[src*="hcaptcha"]',
      'iframe[src*="arkoselabs"]',
      '.cf-turnstile',
      '.g-recaptcha',
      '.h-captcha',
      '#turnstile-wrapper',
      '[data-sitekey]'
    ];

    for (const sel of captchaSelectors) {
      const el = root.querySelector(sel);
      if (el && el.offsetParent !== null) {
        let type = 'CAPTCHA Challenge';
        if (sel.includes('cloudflare') || sel.includes('turnstile')) type = 'Cloudflare Turnstile';
        else if (sel.includes('recaptcha')) type = 'Google reCAPTCHA';
        else if (sel.includes('hcaptcha')) type = 'hCaptcha';
        else if (sel.includes('arkoselabs')) type = 'Arkose Labs Challenge';
        return { detected: true, type, element: el };
      }
    }
    return { detected: false };
  }

  /**
   * Find label text associated with any form control
   */
  function findAssociatedLabel(el) {
    if (!el) return '';
    let texts = [];
    const doc = el.ownerDocument || (typeof document !== 'undefined' ? document : null);
    const escapeCss = (id) => (typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(id) : id.replace(/["\\]/g, '\\$&'));

    // 1. Explicit <label for="id">
    if (el.id && doc && typeof doc.querySelector === 'function') {
      try {
        const label = doc.querySelector(`label[for="${escapeCss(el.id)}"]`);
        if (label && label.textContent) texts.push(label.textContent.trim());
      } catch (_) {}
    }

    // 2. Ancestor <label>
    if (typeof el.closest === 'function') {
      try {
        const parentLabel = el.closest('label');
        if (parentLabel && parentLabel.textContent) {
          texts.push(parentLabel.textContent.trim());
        }
      } catch (_) {}
    }

    // 3. aria-label or aria-labelledby
    if (el.getAttribute && el.getAttribute('aria-label')) {
      texts.push(el.getAttribute('aria-label').trim());
    }
    if (el.getAttribute && el.getAttribute('aria-labelledby') && doc) {
      const ids = el.getAttribute('aria-labelledby').split(' ');
      for (const id of ids) {
        try {
          const labelled = typeof doc.getElementById === 'function' ? doc.getElementById(id) : doc.querySelector(`#${escapeCss(id)}`);
          if (labelled && labelled.textContent) texts.push(labelled.textContent.trim());
        } catch (_) {}
      }
    }

    // 4. placeholder or name attribute
    if (el.placeholder) texts.push(String(el.placeholder).trim());
    if (el.name) texts.push(String(el.name).trim());

    // 5. Surrounding fieldset legend or preceding div
    if (typeof el.closest === 'function') {
      try {
        const fieldset = el.closest('fieldset');
        if (fieldset && typeof fieldset.querySelector === 'function') {
          const legend = fieldset.querySelector('legend');
          if (legend && legend.textContent) texts.push(legend.textContent.trim());
        }
      } catch (_) {}
    }

    const prevSibling = el.previousElementSibling;
    if (prevSibling && (prevSibling.tagName === 'LABEL' || prevSibling.tagName === 'SPAN' || prevSibling.tagName === 'P')) {
      texts.push(prevSibling.textContent.trim());
    }

    return texts.join(' ').replace(/\s+/g, ' ').toLowerCase();
  }

  /**
   * Semantic Field Classifier
   * Maps unstandardized web questions/labels to candidate profile attributes.
   */
  const FIELD_DICTIONARY = {
    first_name: [
      'first name', 'given name', 'forename', 'fname', 'first_name', 'candidate_first_name'
    ],
    last_name: [
      'last name', 'family name', 'surname', 'lname', 'last_name', 'candidate_last_name'
    ],
    full_name: [
      'full name', 'your name', 'legal name', 'candidate name', 'applicant name', 'name'
    ],
    email: [
      'email', 'e-mail', 'email address', 'contact email', 'electronic mail'
    ],
    phone: [
      'phone', 'mobile', 'telephone', 'cell', 'phone number', 'contact number', 'whatsapp'
    ],
    linkedin_url: [
      'linkedin', 'linkedin profile', 'linkedin url', 'social profile'
    ],
    github_url: [
      'github', 'github url', 'github profile', 'git repository'
    ],
    portfolio_url: [
      'portfolio', 'personal website', 'website', 'blog', 'project url', 'portfolio url'
    ],
    city: [
      'city', 'current city', 'metro area', 'town'
    ],
    state_province: [
      'state', 'province', 'region', 'state/province'
    ],
    country: [
      'country', 'nationality', 'country of residence'
    ],
    postal_code: [
      'postal code', 'zip code', 'zip', 'pincode', 'pin code'
    ],
    current_title: [
      'current title', 'job title', 'current role', 'present designation', 'headline'
    ],
    current_company: [
      'current company', 'employer', 'present employer', 'current organization'
    ],
    years_of_experience: [
      'years of experience', 'total experience', 'work experience (years)', 'relevant experience'
    ],
    notice_period_days: [
      'notice period', 'availability', 'how soon can you start', 'lead time', 'days of notice'
    ],
    target_salary: [
      'expected salary', 'desired salary', 'salary expectation', 'expected ctc', 'target compensation'
    ],
    legally_authorized: [
      'legally authorized to work', 'work authorization', 'authorized to work', 'eligible to work', 'right to work'
    ],
    requires_sponsorship: [
      'require sponsorship', 'visa sponsorship', 'will you now or in the future require sponsorship'
    ],
    gender: [
      'gender', 'sex', 'eeo gender'
    ],
    race_ethnicity: [
      'race', 'ethnicity', 'eeo race', 'ethnic background'
    ],
    veteran_status: [
      'veteran status', 'military service', 'veteran'
    ],
    disability_status: [
      'disability', 'disability status', 'physical impairment'
    ]
  };

  /**
   * Classify a field based on label and attributes
   */
  function classifyField(el) {
    const contextText = findAssociatedLabel(el);
    if (!contextText) return null;

    let bestCategory = null;
    let maxScore = 0;

    for (const [category, keywords] of Object.entries(FIELD_DICTIONARY)) {
      for (const kw of keywords) {
        if (contextText.includes(kw)) {
          // Exact keyword match gets high weight
          const score = kw.length / (contextText.length + 1);
          if (score > maxScore) {
            maxScore = score;
            bestCategory = category;
          }
        }
      }
    }

    return bestCategory;
  }

  /**
   * Fill a detected form using candidate profile dataset and optional cognitive Answer Bank resolver
   */
  async function autofillForm(container, candidateProfile = {}, questionResolver = null) {
    const root = container || document;
    let filledCount = 0;
    const filledDetails = [];

    // Collect all inputs, textareas, and selects
    const inputs = Array.from(root.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select, [role="combobox"]'));

    for (const el of inputs) {
      if (el.disabled || el.readOnly) continue;

      const category = classifyField(el);
      const rawLabel = findAssociatedLabel(el);

      let valueToFill = null;

      // 1. Deterministic profile mapping
      if (category) {
        switch (category) {
          case 'first_name':
            valueToFill = candidateProfile.first_name || (candidateProfile.full_name || '').split(' ')[0];
            break;
          case 'last_name':
            valueToFill = candidateProfile.last_name || (candidateProfile.full_name || '').split(' ').slice(1).join(' ');
            break;
          case 'full_name':
            valueToFill = candidateProfile.full_name || `${candidateProfile.first_name || ''} ${candidateProfile.last_name || ''}`.trim();
            break;
          case 'email':
            valueToFill = candidateProfile.email || candidateProfile.account_email;
            break;
          case 'phone':
            valueToFill = candidateProfile.phone;
            break;
          case 'linkedin_url':
            valueToFill = candidateProfile.linkedin_url;
            break;
          case 'github_url':
            valueToFill = candidateProfile.github_url;
            break;
          case 'portfolio_url':
            valueToFill = candidateProfile.portfolio_url;
            break;
          case 'city':
            valueToFill = candidateProfile.city;
            break;
          case 'state_province':
            valueToFill = candidateProfile.state_province || candidateProfile.state;
            break;
          case 'country':
            valueToFill = candidateProfile.country;
            break;
          case 'postal_code':
            valueToFill = candidateProfile.postal_code;
            break;
          case 'current_title':
            valueToFill = candidateProfile.current_title || candidateProfile.headline;
            break;
          case 'current_company':
            valueToFill = candidateProfile.current_company;
            break;
          case 'years_of_experience':
            valueToFill = candidateProfile.years_of_experience;
            break;
          case 'notice_period_days':
            valueToFill = candidateProfile.notice_period_days ? `${candidateProfile.notice_period_days} days` : '30 days';
            break;
          case 'target_salary':
            valueToFill = candidateProfile.target_salary_min || candidateProfile.min_desired_salary;
            break;
          case 'legally_authorized':
            valueToFill = candidateProfile.legally_authorized !== undefined ? candidateProfile.legally_authorized : true;
            break;
          case 'requires_sponsorship':
            valueToFill = candidateProfile.requires_sponsorship !== undefined ? candidateProfile.requires_sponsorship : false;
            break;
          case 'gender':
            valueToFill = candidateProfile.gender || 'Decline to self-identify';
            break;
          case 'race_ethnicity':
            valueToFill = candidateProfile.race_ethnicity || 'Decline to self-identify';
            break;
          case 'veteran_status':
            valueToFill = candidateProfile.veteran_status || 'I am not a protected veteran';
            break;
          case 'disability_status':
            valueToFill = candidateProfile.disability_status || 'No, I do not have a disability';
            break;
        }
      }

      // 2. Cognitive Answer Bank fallback for unmapped or open-ended custom questions
      if ((valueToFill === null || valueToFill === undefined || valueToFill === '') && rawLabel && rawLabel.length > 5) {
        if (typeof questionResolver === 'function') {
          try {
            const resolved = await questionResolver(rawLabel, category);
            if (resolved && (typeof resolved === 'string' || resolved.answer)) {
              valueToFill = typeof resolved === 'string' ? resolved : resolved.answer;
            }
          } catch (_) {}
        }
      }

      if (valueToFill === null || valueToFill === undefined || valueToFill === '') continue;

      let success = false;
      const type = (el.type || '').toLowerCase();
      const tagName = el.tagName.toLowerCase();

      if (type === 'radio') {
        const name = el.name;
        const group = name ? Array.from(root.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`)) : [el];
        success = selectRadioOption(group, valueToFill);
      } else if (type === 'checkbox') {
        success = setCheckboxValue(el, Boolean(valueToFill));
      } else if (tagName === 'select') {
        success = setSelectValue(el, valueToFill);
      } else if (tagName === 'textarea') {
        success = setTextareaValue(el, valueToFill);
      } else if (el.getAttribute('role') === 'combobox') {
        success = await selectCustomDropdown(el, valueToFill);
      } else {
        success = setInputValue(el, valueToFill);
      }

      if (success) {
        filledCount++;
        try {
          if (el.dataset) {
            el.dataset.jfAutofilled = 'true';
            el.dataset.jfOriginalValue = String(valueToFill);
            el.dataset.jfCategory = category || '';
            el.dataset.jfQuestion = rawLabel || '';
          }
        } catch (_) {}
        filledDetails.push({ category, value: valueToFill, label: rawLabel });
      }
    }

    const captchaInfo = detectCaptchaElements(root);

    return {
      filled_count: filledCount,
      details: filledDetails,
      captcha: captchaInfo
    };
  }

  /**
   * Scans container for any fields previously autofilled by the engine that
   * have been modified by the human user.
   */
  function getEditedFields(container) {
    const root = container || document;
    const elements = Array.from(root.querySelectorAll('[data-jf-autofilled="true"]'));
    const edits = [];

    for (const el of elements) {
      let currentVal = '';
      if (el.type === 'checkbox') {
        currentVal = String(el.checked);
      } else if (el.type === 'radio') {
        if (!el.checked) continue;
        currentVal = String(el.value || '');
      } else {
        currentVal = String(el.value || '').trim();
      }

      const origVal = (el.dataset.jfOriginalValue || '').trim();
      if (currentVal && currentVal !== origVal) {
        edits.push({
          element: el,
          question: el.dataset.jfQuestion || findAssociatedLabel(el),
          category: el.dataset.jfCategory || classifyField(el),
          originalValue: origVal,
          currentValue: currentVal,
        });
      }
    }
    return edits;
  }

  return {
    setInputValue,
    setTextareaValue,
    setSelectValue,
    setCheckboxValue,
    selectRadioOption,
    selectCustomDropdown,
    findAssociatedLabel,
    classifyField,
    detectCaptchaElements,
    autofillForm,
    getEditedFields,
    FIELD_DICTIONARY
  };
});
