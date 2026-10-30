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

    for field in ("first_names", "last_names"):
        if data[field]:
            data[field] = data[field][:350]
    if data["born_location"]:
        data["born_location"] = data["born_location"][:250]
    if data["born_date"]:
        data["born_date"] = data["born_date"].isoformat()

    data["missing_data"] = [c for c in REQUIRED_DATA if data.get(c) in (None, "")]
    return data