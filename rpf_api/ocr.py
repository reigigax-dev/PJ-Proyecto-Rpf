import os, re, unicodedata, pytesseract
from django.conf import settings
from datetime import date
from PIL import Image, ImageOps, ImageFilter

SEX_TO_BOOL = {"M": False, "F": True}
REQUIRED_DATA = ["document", "first_names", "last_names", "sex", "born_date"]

MONTHS = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}
LETTERS = "A-ZÁÉÍÓÚÑÜ"
MRZ_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
TO_DIGIT = str.maketrans("OQDILZSBG","000115586")

def _configure_tesseract():
    cmd =  None
    try:
        cmd = getattr(settings, "TESSERACT_CMD", None)
    except Exception:
        pass
    cmd = cmd or os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

def _prepare(file):
    file.seek(0)
    img = ImageOps.exif_transpose(Image.open(file))
    file.seek(0)
    img = ImageOps.grayscale(img)
    if img.width < 1600:
        factor = 1600 / img.width
        img = img.resize((1600, int(img.height * factor)), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    return img.filter(ImageFilter.SHARPEN)

def _ocr(img, config=""):
    try:
        return pytesseract.image_to_string(img, lang="spa", config=config)
    except:
        return pytesseract.image_to_string(img, config=config)

<<<<<<< HEAD


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



=======
>>>>>>> parent of 432e04e (Se finaliza* la funcion de escaneo de carnet de identidad (se presentan inconvenientes para detectar la ubicacion de nacimiento y el sexo es detectado por el contrario al del carnet))
def _without_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")

def _clave(text):
    return re.sub(r"[^A-Z]", "", _without_accents(text.upper()))

def rut_validation(rut):
    clean = re.sub(r"[^0-9Kk]", "", rut).upper()
    if len(clean) < 2 or not clean[:-1].isdigit():
        return False
    body, vd = clean[:-1], clean[-1]
    sumation, factor = 0, 2
    for d in reversed(body):
        sumation += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    verification = {11: "0", 10: "K"}.get(11 - sumation % 11, str(11 - sumation % 11))
    return vd == verification 

def rut_unformatted(rut):
    return re.sub(r"[^0-9Kk]", "", rut).upper()

def _vd_mrz(field):
    pesos, total = (7, 3, 1), 0
    for i, c in enumerate(field):
        value = int(c) if c.isdigit() else (ord(c) - 55 if c.isalpha() else 0)
        total += value * pesos[i % 3]
    return str(total % 10)

def _date_mrz(yymmdd):
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    century = 2000 if 2000 + yy <= date.today().year else 1900
    return date(century + yy, mm, dd)


def read_mrz(img):
    text = _ocr(img, config=f"--psm 6 -c tessedit_char_whitelist={MRZ_CHARS}")
    lines = [re.sub(r"\s+", "", l).upper() for l in text.splitlines()]
    lines = [l for l in lines if len(l) >= 20 and "<" in l]

    for i, line in enumerate(lines):
        if re.match(r"^I[A-Z<]CHL", line) and i + 2 < len(lines):
            return parse_mrz(*lines[i:i + 3])
    for i, line in enumerate(lines):
        if re.match(r"^I[0-9O]{6}[0-9O][MF<]", line) and i + 1 < len(lines):
            return parse_mrz("", line, lines[i + 1])
    return{}

def parse_mrz(line1, line2, line3):
    data = {}
    line1, line2 = line1.ljust(30, "<"), line2.ljust(30, "<")

    if line1.strip("<"):
        number = line1[5:14].translate(TO_DIGIT)
        if number.isdigit() and _vd_mrz(number) == line1[14].translate(TO_DIGIT):
            data["document_number"] = int(number)
        m = re.search(r"(\d{7,8})[<\-]?([0-9K])", line1[15:].translate(str.maketrans("O", "0")))
        if m and rut_validation(m.group(1) + m.group(2)):
            data["document"] = m.group(1) + m.group(2)

    born_date = line2[0:6].translate(TO_DIGIT)
    if born_date.isdigit() and _vd_mrz(born_date) == line2[6].translate(TO_DIGIT):
        try:
            data["born_date"] = _date_mrz(born_date)
        except ValueError:
            pass
    if line2[7] in SEX_TO_BOOL:
        data["sex"] = SEX_TO_BOOL[line2[7]]

    line3 = re.sub(r"[<K]{3,}$", "", line3.strip("<"))
    if "<<" in line3:
        last_names, first_names = line3.split("<<", 1)
        last_names = last_names.replace("<", " ").strip()
        first_names = first_names.replace("<", " ").strip()
        if last_names and first_names:
            data["last_names"] = first_names.title()
            data["first_names"] = last_names.title()
    return data

def _line_of_letters(lines):
    return [l for l in lines if re.fullmatch(rf"[{LETTERS}' -]{{2,}}", l)]

def parse_front(text):
    data = {}
    lines = [re.sub(r"\s+", " ", l).strip().upper() for l in text.splitlines()]
    lines = [l for l in lines if l]

    for m in re.finditer(r"\b(\d{1,2}\.?\d{3}\s?-\s?[\dK])\b", text.upper()):
        if rut_validation(m.group(1)):
            data["document"] = rut_unformatted(m.group(1))
            break

    i_last_name = next((i for i, l in enumerate(lines) if "APELLIDO" in l), None)
    i_first_name = next((i for i, l in enumerate(lines) if "NOMBRE" in l), None)
    if i_last_name is not None and i_first_name is not None and i_last_name < i_first_name:
        last_names = _line_of_letters(lines[i_last_name + 1:i_first_name])
        if last_names:
            data["last_names"] = " ".join(last_names).title()
    if i_first_name is not None:
        first_names = []
        for l in lines[i_first_name + 1:]:
            if re.search(r"NACIONAL|SEXO|FECHA|RUN", l):
                break
            first_names += _line_of_letters([l])
        if first_names:
            data["first_names"] = " ".join(first_names).title()

    m = re.search(r"SEXO.{0,60}?\b([MF])\b", text.upper(), re.S)
    if m:
        data["sex"] = SEX_TO_BOOL[m.group(1)]

    dates = []
    pattern = r"\b(\d{1,2})\s*[ /.\-]\s*([A-Z]{3}|\d{1,2})\s*[ /.\-]\s*(\d{4})\b"
    for day, month, year in re.findall(pattern, _without_accents(text.upper())):
        try:
            dates.append(date(int(year), MONTHS[month] if month.isalpha() else int(month), int(day)))
        except (KeyError, ValueError):
            continue
    if dates:
        data["born_date"] = min(dates)

    m = re.search(r"\b(\d{3}\.\d{3}\.\d{3})\b", text)
    if m:
        data["document_number"] = int(m.group(1).replace(".", ""))
    return data

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


def scan_carnet(frontal_img, back_img):
    _configure_tesseract()
    frontal_img = _prepare(frontal_img)
    back_img = _prepare(back_img)

<<<<<<< HEAD
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
=======
    front = parse_front(_ocr(frontal_img))
    mrz = read_mrz(back_img)
    back_text = _ocr(back_img)

    data = {}
    for field in ("born_date", "sex", "document_number", "document"):
        data[field] = mrz.get(field, front.get(field))
    if data["document"] is None:
        data["document"] = front.get("document")

    for field in ("first_names", "last_names"):
        f, m = front.get(field), mrz.get(field)
        if f and m:
            data[field] = f if _clave(f) == _clave(m) else m
        else:
            data[field] = f or m

    data["born_location"] = read_born_place(back_text)
>>>>>>> parent of 432e04e (Se finaliza* la funcion de escaneo de carnet de identidad (se presentan inconvenientes para detectar la ubicacion de nacimiento y el sexo es detectado por el contrario al del carnet))

    for field in ("first_names", "last_names"):
        if data[field]:
            data[field] = data[field][:350]
    if data["born_location"]:
        data["born_location"] = data["born_location"][:250]
    if data["born_date"]:
        data["born_date"] = data["born_date"].isoformat()

    data["missing_data"] = [c for c in REQUIRED_DATA if data.get(c) in (None, "")]
<<<<<<< HEAD
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
=======
    return data
>>>>>>> parent of 432e04e (Se finaliza* la funcion de escaneo de carnet de identidad (se presentan inconvenientes para detectar la ubicacion de nacimiento y el sexo es detectado por el contrario al del carnet))
