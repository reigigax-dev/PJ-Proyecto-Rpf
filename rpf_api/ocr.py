import os, re, unicodedata, pytesseract, cv2
import numpy as np
from django.conf import settings
from datetime import date
from PIL import Image, ImageOps, ImageFilter

SEX_TO_BOOL = {"M": False, "F": True}
REQUIRED_DATA = ["document", "first_names", "last_names", "sex", "born_date"]

MONTHS = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}
LETTERS = "A-ZÁÉÍÓÚÑÜ"
MRZ_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
DIGITLIKE = "0-9OQDILZSBG"
TO_DIGIT = str.maketrans("OQDILZSBG", "000112586")
TO_LETTER = str.maketrans("0158", "OISB")

CARD_W, CARD_H = 1712, 1080
LABEL_WORDS = {
    "APELLIDOS", "APELLIDO", "NOMBRES", "NOMBRE", "NACIONALIDAD", "SEXO",
    "FECHA", "NACIMIENTO", "NUMERO", "DOCUMENTO", "EMISION", "VENCIMIENTO",
    "CHILENA", "CHILENO", "RUN", "REPUBLICA", "CHILE", "CEDULA", "IDENTIDAD",
    "SURNAMES", "NAMES", "SEX", "NATIONALITY"
}

def _configure_tessereact():
    cmd = getattr(settings, "TESSERACT_CMD", None) or os.environ.get("TESSERACT_CMD")
    if  cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

def _ocr(img, config=""):
    try:
        return pytesseract.image_to_string(img, lang="spa", config=config)
    except pytesseract.TesseractNotFoundError:
        raise
    except pytesseract.TesseractError:
        return pytesseract.image_to_string(img, config=config)



def _load(file):
    file.seek(0)
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    file.seek(0)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def _order_points(pts):
    s, d = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
    return np.array([
        pts[np.argmin(s)],
        pts[np.argmin(d)],
        pts[np.argmax(s)],
        pts[np.argmax(d)]
    ], dtype="float32")

def _find_card(bgr):
    h, w = bgr.shape[:2]
    scale = 1000 / max(h, w)
    small = cv2.resize(bgr, (int(w * scale), int(h * scale)))
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.dilate(cv2.Canny(gray, 30, 100), np.ones((5, 5), np.uint8))
    contours = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    area_img = small.shape[0] * small.shape[1]

    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(c) < 0.25 * area_img:
            break
        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if not rw or not rh:
            continue
        ratio = max(rw, rh) / min(rw, rh)
        if not 1.35 <= ratio <= 1.85:
            continue
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        pts = approx.reshape(-1, 2) if len(approx) == 4 else cv2.boxPoints(rect)
        src = _order_points(pts.astype("float32") / scale)
        if np.linalg.norm(src[0] - src[1]) < np.linalg.norm(src[1] - src[2]):
            src = np.roll(src, -1, axis=0)
        dst = np.array([[0, 0], [CARD_W - 1, 0], [CARD_W - 1, CARD_H - 1], [0, CARD_H - 1]], "float32")
        return cv2.warpPerspective(bgr, cv2.getPerspectiveTransform(src, dst), (CARD_W, CARD_H))
    return None

def _normalize(bgr):
    card = _find_card(bgr)
    if card is not None:
        return card, True
    h, w = bgr.shape[:2]
    f = CARD_W / w if w < CARD_W else 1.0
    return cv2.resize(bgr, (int(w * f), int(h * f)), interpolation=cv2.INTER_CUBIC), False

def _gray(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

def _clean(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    background = cv2.medianBlur(cv2.dilate(gray, np.ones((7, 7), np.uint8)), 31)
    flat = cv2.divide(gray, background, scale=255)
    _, bw = cv2.threshold(flat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.medianBlur(bw, 3)

def _to_pil(arr):
    return Image.fromarray(arr)


def _legacy(bgr):
    img = ImageOps.grayscale(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
    if img.width < 1600:
        img = img.resize((1600, int(img.height * 1600 / img.width)), Image.LANCZOS)
    return ImageOps.autocontrast(img).filter(ImageFilter.SHARPEN)



def rut_unformatted(rut):
    return re.sub(r"[^0-9Kk]", "", rut).upper()

def rut_validation(rut):
    clean = rut_unformatted(rut)
    if len(clean) < 2 or not clean[:-1].isdigit():
        return False
    body, vd = clean[:-1], clean[-1]
    total, factor = 0, 2
    for d in reversed(body):
        total += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    expected = {11: "0", 10: "K"}.get(11 - total % 11, str(11 - total % 11))
    return vd == expected

def find_rut(text):
    t = text.upper()
    pattern = rf"([{DIGITLIKE}]{{1,2}})\s*[.,·' ]?\s*([{DIGITLIKE}]{{3}})\s*[.,·' ]?\s*([{DIGITLIKE}]{{3}})\s*[-–—~=]\s*([0-9K])"
    for m in re.finditer(pattern, t):
        candidate = "".join(m.groups()[:3]).translate(TO_DIGIT) + m.group(4)
        if candidate[:-1].isdigit() and rut_validation(candidate):
            return candidate
    
    for line in t.splitlines():
        if "RUN" in line or "RUT" in line:
            digits = re.sub(r"[^0-9K]", "", line.split("RU", 1)[1][1:])
            if len(digits) in (8, 9) and rut_validation(digits):
                return digits
    return None



def _vd_mrz(field):
    weights, total = (7, 3, 1), 0
    for i, c in enumerate(field):
        value = int(c) if c.isdigit() else (ord(c) - 55 if c.isalpha() else 0)
        total += value * weights[i % 3]
    return str(total % 10)

def _date_mrz(yymmdd):
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    century = 2000 if 2000 + yy <= date.today().year else 1900
    return date(century + yy, mm, dd)

def _mrz_lines(text):
    lines = []
    for line in text.upper().splitlines():
        line = re.sub(r"\s+", "", line).replace("«", "<<")
        if len(line) >= 15 and ("<" in line or "CHL" in line):
            lines.append(line)
    return lines

def parse_mrz(text):
    data = {}
    lines = _mrz_lines(text)

    l2_index = None
    for i, line in enumerate(lines):
        m = re.search(rf"([{DIGITLIKE}]{{6}})([{DIGITLIKE}])([MF<])([{DIGITLIKE}]{{6}})([{DIGITLIKE}])", line)
        if not m:
            continue
        born, vd = m.group(1).translate(TO_DIGIT), m.group(2).translate(TO_DIGIT)
        if _vd_mrz(born) == vd:
            try:
                data["born_date"] = _date_mrz(born)
                l2_index = i
            except ValueError:
                pass
        if m.group(3) in SEX_TO_BOOL:
            data["sex"] = SEX_TO_BOOL[m.group(3)]
        if l2_index is not None:
            break

    for line in lines:
        m = re.search(r"[I1L][A-Z<0-9]?CHL", line)
        if not m:
            continue
        rest = line[m.end():]
        number, vd = rest[:9].translate(TO_DIGIT), rest[9:10].translate(TO_DIGIT)
        if number.isdigit() and vd and _vd_mrz(number) == vd:
            data["document_number"] = int(number)
            rest = rest[10:]
        for r in re.finditer(rf"([{DIGITLIKE}]{{7,8}})<?([0-9K])", rest):
            run = r.group(1).translate(TO_DIGIT) + r.group(2)
            if rut_validation(run):
                data["document"] = run
                break
        break

    candidates = lines[l2_index + 1:] if l2_index is not None else lines
    for line in candidates:
        if "<<" not in line or "CHL" in line[:6]:
            continue
        letters = re.sub(r"[^A-Z<]", "", line)
        if len(letters) < 0.9 * len(line):
            continue
        line = re.sub(r"^<+", "", letters)
        last, _, first = line.partition("<<")
        first = re.sub(r"<[<KC]*$", "", first).split("<<")[0]
        last, first = last.replace("<", " ").strip(), first.replace("<", " ").strip()
        if len(last) >= 2 and len(first) >= 2:
            data["last_names"] = last.title()
            data["first_names"] = first.title()
            break
    return data

def read_back(bgr):
    card, found = _normalize(bgr)
    h = card.shape[0]
    zone = card[int(h * 0.55):, :] if found else card
    config = f"--psm 6 -c tessedit_char_whitelist={MRZ_CHARS}"
    texts, mrz = [], {}
    for variant in (_clean(zone), _gray(zone)):
        text = _ocr(_to_pil(variant), config=config)
        texts.append(text)
        found_data = parse_mrz(text)
        for k, v in found_data.items():
            mrz.setdefault(k, v)
        if all(k in mrz for k in ("born_date", "last_names", "first_names", "document")):
            break
    general, born_place = [], None
    for text in _born_place_texts(card, bgr):
        general.append(text)
        born_place = read_born_place(text)
        if born_place:
            break
    return mrz, born_place, {"card_found": found, "mrz_text": texts, "text": general}



def _without_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")

def _clave(text):
    return re.sub(r"[^A-Z]", "", _without_accents(text.upper()))

def _is_label(line, *words):
    plain = _clave(line)
    return any(w in plain for w in words)

def _name_tokens(line):
    tokens = re.findall(rf"[{LETTERS}]{{2,}}", line.upper())
    return [t for t in tokens if _without_accents(t) not in LABEL_WORDS]

def _parse_date(day, month, year):
    month = month.translate(TO_LETTER) if re.search(r"[A-Z]", month) else month.translate(TO_DIGIT)
    month_num = MONTHS.get(month[:3]) if month.isalpha() else int(month)
    return date(int(year.translate(TO_DIGIT)), month_num, int(day.translate(TO_DIGIT)))

def _dates(line):
    found = []
    pattern = rf"\b([{DIGITLIKE}]{{1,2}})\s*[ /.\-]\s*([A-Z0-9]{{3}}|\d{{1,2}})\s*[ /.\-]\s*([{DIGITLIKE}]{{4}})"
    for d, m, y in re.findall(pattern, _without_accents(line.upper())):
        try:
            found.append(_parse_date(d, m, y))
        except (TypeError, ValueError):
            continue
    return found

def _names_by_position(lines):
    start = next((i for i, l in enumerate(lines) if _is_label(l, "IDENTIDAD", "CEDULA")), -1)
    end = next((i for i, l in enumerate(lines) if _is_label(l, "CHILEN", "NACIONAL", "EXTRANJER")), None)
    if end is None or end <= start:
        return {}
    name_lines = []
    for l in lines[start + 1:end]:
        tokens = _name_tokens(l)
        if tokens and sum(map(len, tokens)) >= 0.7 * len(re.sub(rf"[^{LETTERS}0-9]", "", l)):
            name_lines.append(tokens)
    if len(name_lines) < 2:
        return {}
    name_lines = name_lines[-3:]
    return {
        "last_names": " ".join(t for ts in name_lines[:-1] for t in ts).title(),
        "first_names": " ".join(name_lines[-1]).title(),
    }

def _accented(mrz_value, front_texts):
    words = set(re.findall(rf"[{LETTERS}]{{2,}}", " ".join(front_texts).upper()))
    result = []
    for token in mrz_value.upper().split():
        match = next((w for w in words if w != token and _without_accents(w) == token), None)
        result.append(match or token)
    return " ".join(result).title()

def parse_front(text):
    data = {}
    lines = [re.sub(r"\s+", " ", l).strip().upper() for l in text.splitlines()]
    lines = [l for l in lines if l]

    rut = find_rut(text)
    if rut:
        data["document"] = rut

    i_last = next((i for i, l in enumerate(lines) if _is_label(l, "APELLIDO", "PELLIDO")), None)
    i_first = next((i for i, l in enumerate(lines) if _is_label(l, "NOMBRE", "OMBRES")), None)
    stop = ("NACIONAL", "SEXO", "FECHA", "NACIMIENTO", "RUN", "DOCUMENTO")

    if i_last is not None and i_first is not None and i_last < i_first:
        tokens = [t for l in lines[i_last + 1:i_first] for t in _name_tokens(l)]
        if tokens:
            data["last_names"] = " ".join(tokens).title()
    if i_first is not None:
        tokens = []
        for l in lines[i_first + 1:i_first + 3]:
            if _is_label(l, *stop):
                break
            tokens += _name_tokens(l)
        if tokens:
            data["first_names"] = " ".join(tokens).title()
    if i_last is None and i_first is None:
        data.update(_names_by_position(lines))

    for i, l in enumerate(lines[:-1]):
        if _is_label(l, "SEXO"):
            m = re.search(r"(?:^|\s)([MF])(?:\s|$)", lines[i + 1])
            if m:
                data["sex"] = SEX_TO_BOOL[m.group(1)]
            break

    for i, l in enumerate(lines[:-1]):
        if _is_label(l, "NACIMIENTO"):
            found = _dates(lines[i + 1])
            if found:
                data["born_date"] = found[0]
            break
    if "born_date" not in data:
        past = [d for l in lines for d in _dates(l) if 1900 < d.year and d < date.today()]
        if past:
            data["born_date"] = min(past)

    m = re.search(rf"([{DIGITLIKE}]{{3}})[.,]([{DIGITLIKE}]{{3}})[.,]([{DIGITLIKE}]{{3}})", text.upper())
    if m:
        number = "".join(m.groups()).translate(TO_DIGIT)
        if number.isdigit():
            data["document_number"] = int(number)
    return data

def read_front(bgr):
    card, found = _normalize(bgr)
    data, texts = {}, []
    variants = [_clean(card), _gray(card)]
    if found:
        variants.append(_clean(card[:, int(CARD_W * 0.28):]))
    for variant in variants:
        text = _ocr(_to_pil(variant), config="--psm 6")
        texts.append(text)
        for k, v in parse_front(text).items():
            data.setdefault(k, v)
        if all(k in data for k in ("document", "first_names", "last_names", "born_date")):
            break
    return data, {"card_found": found, "text": texts}



def read_born_place(text):
    lines = [l.strip() for l in text.upper().splitlines() if l.strip()]
    for line in lines:
        m = re.search(rf"NAC[A-Z0-9ÁÉÍÓÚ]{{1,3}}\s*EN\s*[:.;,]?\s*([{LETTERS}][{LETTERS} .'-]{{2,}})", line)
        if not m:
            continue
        value = _place_words(re.split(r"\s{2,}|PROFESI", m.group(1))[0])
        if value:
            return value

    for i, line in enumerate(lines):
        if re.search(r"PROF[EÉ]S", _without_accents(line)) and i > 0:
            previous = lines[i - 1].split(":")[-1]
            value = _place_words(previous)
            if value and _without_accents(value.upper()).replace(" ", "") not in LABEL_WORDS:
                return value
    return None


def _place_words(text):
    words = [w for w in re.findall(rf"[{LETTERS}]+", text.upper()) if len(w) >= 2]
    letters = len(re.sub(rf"[^{LETTERS}]", "", text.upper()))
    if not words or sum(map(len, words)) < 0.8 * letters:
        return None
    return " ".join(words).title()


def _born_place_texts(card, original):
    h = card.shape[0]
    top = card[: int(h * 0.5), :]
    top = cv2.resize(top, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    yield _ocr(_to_pil(_gray(card)))
    yield _ocr(_legacy(original))
    yield _ocr(_to_pil(cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)))
    yield _ocr(_to_pil(_clean(top)))
    yield _ocr(_to_pil(cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)))



def _merge_name(front_value, mrz_value, front_texts):
    if front_value and mrz_value and _clave(front_value) == _clave(mrz_value):
        return front_value
    if mrz_value:
        return _accented(mrz_value, front_texts)
    return front_value

def scan_carnet(frontal_img, back_img, debug=False):
    _configure_tessereact()
    front_bgr, back_bgr = _load(frontal_img), _load(back_img)

    mrz, born_place, back_dbg = read_back(back_bgr)
    if not mrz:
        mrz, born_place, back_dbg = read_back(cv2.rotate(back_bgr, cv2.ROTATE_180))

    front, front_dbg = read_front(front_bgr)
    if not front.get("document") and not front.get("last_names"):
        rotated, rotated_dbg = read_front(cv2.rotate(front_bgr, cv2.ROTATE_180))
        if len(rotated) > len(front):
            front, front_dbg = rotated, rotated_dbg

    data = {}
    for field in ("born_date", "sex", "document_number", "document"):
        data[field] = mrz.get(field) if mrz.get(field) is not None else front.get(field)
    front_texts = front_dbg["text"]
    data["first_names"] = _merge_name(front.get("first_names"), mrz.get("first_names"), front_texts)
    data["last_names"] = _merge_name(front.get("last_names"), mrz.get("last_names"), front_texts)
    data["born_location"] = born_place

    for field, size in (("first_names", 350), ("last_names", 350), ("born_location", 250)):
        if data[field]:
            data[field] = data[field][:size]
    data["born_date"] = _to_iso(data["born_date"])

    data["missing_data"] = [c for c in REQUIRED_DATA if data.get(c) in (None, "")]
    if debug:
        data["debug"] = {
            "front": front_dbg,
            "back": back_dbg,
            "front_data": _jsonable(front),
            "mrz_data": _jsonable(mrz),
        }
    return data

def _jsonable(d):
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in d.items()}

def _to_iso(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        y, mo, d = m.groups()
    else:
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", text)
        if not m:
            return None
        d, mo, y = m.groups()
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None