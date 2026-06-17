# -*- coding: utf-8 -*-
"""
Pure-Python Arabic/Urdu contextual shaper + bidi reordering.
No external libraries. Good enough for headline/summary display in Kivy.

Covers: letter joining (isolated/initial/medial/final forms) for the
Arabic + Urdu letter set, lam-alef ligatures, and a simple bidi pass
that reverses RTL runs while keeping LTR runs (numbers, latin) in order.
"""

# (base_char): (isolated, final, initial, medial)
_FORMS = {
    "\u0621": ("\uFE80", "\uFE80", "\uFE80", "\uFE80"),  # hamza
    "\u0622": ("\uFE81", "\uFE82", "\uFE81", "\uFE82"),  # alef madda
    "\u0623": ("\uFE83", "\uFE84", "\uFE83", "\uFE84"),  # alef hamza above
    "\u0624": ("\uFE85", "\uFE86", "\uFE85", "\uFE86"),  # waw hamza
    "\u0625": ("\uFE87", "\uFE88", "\uFE87", "\uFE88"),  # alef hamza below
    "\u0626": ("\uFE89", "\uFE8A", "\uFE8B", "\uFE8C"),  # yeh hamza
    "\u0627": ("\uFE8D", "\uFE8E", "\uFE8D", "\uFE8E"),  # alef
    "\u0628": ("\uFE8F", "\uFE90", "\uFE91", "\uFE92"),  # beh
    "\u0629": ("\uFE93", "\uFE94", "\uFE93", "\uFE94"),  # teh marbuta
    "\u062A": ("\uFE95", "\uFE96", "\uFE97", "\uFE98"),  # teh
    "\u062B": ("\uFE99", "\uFE9A", "\uFE9B", "\uFE9C"),  # theh
    "\u062C": ("\uFE9D", "\uFE9E", "\uFE9F", "\uFEA0"),  # jeem
    "\u062D": ("\uFEA1", "\uFEA2", "\uFEA3", "\uFEA4"),  # hah
    "\u062E": ("\uFEA5", "\uFEA6", "\uFEA7", "\uFEA8"),  # khah
    "\u062F": ("\uFEA9", "\uFEAA", "\uFEA9", "\uFEAA"),  # dal
    "\u0630": ("\uFEAB", "\uFEAC", "\uFEAB", "\uFEAC"),  # thal
    "\u0631": ("\uFEAD", "\uFEAE", "\uFEAD", "\uFEAE"),  # reh
    "\u0632": ("\uFEAF", "\uFEB0", "\uFEAF", "\uFEB0"),  # zain
    "\u0633": ("\uFEB1", "\uFEB2", "\uFEB3", "\uFEB4"),  # seen
    "\u0634": ("\uFEB5", "\uFEB6", "\uFEB7", "\uFEB8"),  # sheen
    "\u0635": ("\uFEB9", "\uFEBA", "\uFEBB", "\uFEBC"),  # sad
    "\u0636": ("\uFEBD", "\uFEBE", "\uFEBF", "\uFEC0"),  # dad
    "\u0637": ("\uFEC1", "\uFEC2", "\uFEC3", "\uFEC4"),  # tah
    "\u0638": ("\uFEC5", "\uFEC6", "\uFEC7", "\uFEC8"),  # zah
    "\u0639": ("\uFEC9", "\uFECA", "\uFECB", "\uFECC"),  # ain
    "\u063A": ("\uFECD", "\uFECE", "\uFECF", "\uFED0"),  # ghain
    "\u0640": ("\u0640", "\u0640", "\u0640", "\u0640"),  # tatweel
    "\u0641": ("\uFED1", "\uFED2", "\uFED3", "\uFED4"),  # feh
    "\u0642": ("\uFED5", "\uFED6", "\uFED7", "\uFED8"),  # qaf
    "\u0643": ("\uFED9", "\uFEDA", "\uFEDB", "\uFEDC"),  # kaf
    "\u0644": ("\uFEDD", "\uFEDE", "\uFEDF", "\uFEE0"),  # lam
    "\u0645": ("\uFEE1", "\uFEE2", "\uFEE3", "\uFEE4"),  # meem
    "\u0646": ("\uFEE5", "\uFEE6", "\uFEE7", "\uFEE8"),  # noon
    "\u0647": ("\uFEE9", "\uFEEA", "\uFEEB", "\uFEEC"),  # heh
    "\u0648": ("\uFEED", "\uFEEE", "\uFEED", "\uFEEE"),  # waw
    "\u0649": ("\uFEEF", "\uFEF0", "\uFEEF", "\uFEF0"),  # alef maksura
    "\u064A": ("\uFEF1", "\uFEF2", "\uFEF3", "\uFEF4"),  # yeh
    # --- Urdu-specific letters (map to closest Arabic presentation forms) ---
    "\u0679": ("\uFB66", "\uFB67", "\uFB68", "\uFB69"),  # tteh (ٹ)
    "\u067E": ("\uFB56", "\uFB57", "\uFB58", "\uFB59"),  # peh (پ)
    "\u0686": ("\uFB7A", "\uFB7B", "\uFB7C", "\uFB7D"),  # tcheh (چ)
    "\u0688": ("\uFB88", "\uFB89", "\uFB88", "\uFB89"),  # ddal (ڈ)
    "\u0691": ("\uFB8C", "\uFB8D", "\uFB8C", "\uFB8D"),  # rreh (ڑ)
    "\u0698": ("\uFB8A", "\uFB8B", "\uFB8A", "\uFB8B"),  # jeh (ژ)
    "\u06A9": ("\uFB8E", "\uFB8F", "\uFB90", "\uFB91"),  # keheh (ک)
    "\u06AF": ("\uFB92", "\uFB93", "\uFB94", "\uFB95"),  # gaf (گ)
    "\u06BA": ("\uFB9E", "\uFB9F", "\uFB9E", "\uFB9F"),  # noon ghunna (ں)
    "\u06BE": ("\uFBAA", "\uFBAB", "\uFBAC", "\uFBAD"),  # heh doachashmee (ھ)
    "\u06C1": ("\uFBA6", "\uFBA7", "\uFBA8", "\uFBA9"),  # heh goal (ہ)
    "\u06CC": ("\uFBFC", "\uFBFD", "\uFBFE", "\uFBFF"),  # farsi yeh (ی)
    "\u06D2": ("\uFBAE", "\uFBAF", "\uFBAE", "\uFBAF"),  # yeh barree (ے)
}

# Letters that do NOT connect to the following letter (right-joining only)
_NON_CONNECTING = set("\u0622\u0623\u0624\u0625\u0627\u0629\u062F\u0630"
                      "\u0631\u0632\u0648\u0649\u0688\u0691\u0698\u06D2"
                      "\u06BA\u06C1\u0621")

# Lam-Alef ligatures: (alef) -> (isolated, final)
_LAM_ALEF = {
    "\u0622": ("\uFEF5", "\uFEF6"),
    "\u0623": ("\uFEF7", "\uFEF8"),
    "\u0625": ("\uFEF9", "\uFEFA"),
    "\u0627": ("\uFEFB", "\uFEFC"),
}

# Harakat / combining marks — invisible spacing, attach to previous letter
_MARKS = set("\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0653\u0654"
             "\u0655\u0656\u0670\u06D6\u06D7\u06D8\u06D9\u06DA\u06DB\u06DC"
             "\u06DF\u06E0\u06E1\u06E2\u06E3\u06E4\u06E7\u06E8\u06EA\u06EB"
             "\u06EC\u06ED")


def _is_arabic(ch):
    return ch in _FORMS or ch in _MARKS


def _connects_after(ch):
    """True if ch can join to the letter on its left (next in logical order)."""
    return ch in _FORMS and ch not in _NON_CONNECTING and ch != "\u0640"


def _connects_before(ch):
    """True if ch can join to the letter on its right (previous letter)."""
    return ch in _FORMS  # all forms can accept a join from the right


def _shape_word(word):
    """Apply contextual forms to one run of arabic chars (logical order)."""
    # separate marks but remember position
    chars = list(word)
    out = []
    n = len(chars)
    i = 0
    # Precompute "letter" positions ignoring marks for join logic
    letters = [c for c in chars if c not in _MARKS]
    # Build shaped letters
    shaped = []
    for idx, ch in enumerate(letters):
        if ch not in _FORMS:
            shaped.append(ch)
            continue
        prev = letters[idx - 1] if idx > 0 else None
        nxt = letters[idx + 1] if idx < len(letters) - 1 else None

        join_prev = bool(prev and _connects_after(prev) and _connects_before(ch))
        join_next = bool(nxt and _connects_after(ch) and _connects_before(nxt))

        # Lam-Alef ligature
        if ch == "\u0644" and nxt in _LAM_ALEF:
            iso, fin = _LAM_ALEF[nxt]
            shaped.append(fin if join_prev else iso)
            # skip the alef next round by marking it
            letters[idx + 1] = ""  # consumed
            continue
        if ch == "":  # consumed alef
            continue

        iso, fin, ini, med = _FORMS[ch]
        if join_prev and join_next:
            shaped.append(med)
        elif join_prev and not join_next:
            shaped.append(fin)
        elif not join_prev and join_next:
            shaped.append(ini)
        else:
            shaped.append(iso)

    # Re-insert marks right after their base letter (kept inline)
    # Simple approach: rebuild by walking original, swapping base letters
    result = []
    li = 0
    base_iter = [s for s in shaped if s != ""]
    bi = 0
    for ch in chars:
        if ch in _MARKS:
            result.append(ch)
        else:
            if bi < len(base_iter):
                result.append(base_iter[bi])
                bi += 1
    return "".join(result)


def shape_arabic(text):
    """Contextual-join an Arabic/Urdu string (no reordering)."""
    if not text:
        return text
    out = []
    buf = []
    for ch in text:
        if _is_arabic(ch):
            buf.append(ch)
        else:
            if buf:
                out.append(_shape_word("".join(buf)))
                buf = []
            out.append(ch)
    if buf:
        out.append(_shape_word("".join(buf)))
    return "".join(out)


def _is_rtl_char(ch):
    return ("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F"
            or "\uFB50" <= ch <= "\uFDFF" or "\uFE70" <= ch <= "\uFEFF")


def reorder_bidi(text):
    """
    Minimal bidi: reverse the whole string for display, but keep
    contiguous LTR runs (latin words, numbers) in their normal order.
    Good enough for mixed Urdu/number headlines.
    """
    if not text:
        return text
    # Split into runs of RTL vs LTR(neutral attaches to LTR)
    runs = []
    cur = []
    cur_rtl = None
    for ch in text:
        if _is_rtl_char(ch):
            r = True
        elif ch.isalpha() or ch.isdigit():
            r = False
        else:
            r = cur_rtl if cur_rtl is not None else True
        if cur_rtl is None:
            cur_rtl = r
        if r == cur_rtl:
            cur.append(ch)
        else:
            runs.append((cur_rtl, "".join(cur)))
            cur = [ch]
            cur_rtl = r
    if cur:
        runs.append((cur_rtl, "".join(cur)))

    # For display: reverse run order, and reverse chars within RTL runs
    out = []
    for is_rtl, chunk in reversed(runs):
        if is_rtl:
            out.append(chunk[::-1])
        else:
            out.append(chunk)
    return "".join(out)


def shape_urdu(text):
    """Full pipeline: contextual join then bidi reorder for Kivy display."""
    if not text:
        return ""
    try:
        return reorder_bidi(shape_arabic(text))
    except Exception:
        return text


if __name__ == "__main__":
    samples = [
        "پاکستان میں آج کی خبریں",
        "اسلام آباد: حکومت کا اہم فیصلہ",
        "BR Fragrance خوشبو کی دنیا",
        "اردو نیوز ڈیلی 2024",
    ]
    for s in samples:
        print("IN :", s)
        print("OUT:", shape_urdu(s))
        print("LEN:", len(s), "->", len(shape_urdu(s)))
        print("-" * 40)
