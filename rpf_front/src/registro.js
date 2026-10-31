// Lógica compartida de los campos de EventSignUp (tabla editable y formulario).

// Misma regla que ocr.py: SEX_TO_BOOL = {"M": False, "F": True}
export const SEXO = { true: "F", false: "M" };

export const VACIO = {
    document: "",
    first_names: "",
    last_names: "",
    sex: "M",
    born_date: "",
    born_location: "",
    document_number: "",
};

export function formatearRut(rut) {
    if (!rut) return "";
    const limpio = String(rut).replace(/[^0-9kK]/g, "").toUpperCase();
    if (limpio.length < 2) return limpio;
    const cuerpo = limpio.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return `${cuerpo}-${limpio.slice(-1)}`;
}

function rutValido(rut) {
    const limpio = String(rut).replace(/[^0-9kK]/g, "").toUpperCase();
    if (limpio.length < 2 || !/^\d+$/.test(limpio.slice(0, -1))) return false;
    let suma = 0, factor = 2;
    for (const d of limpio.slice(0, -1).split("").reverse()) {
        suma += Number(d) * factor;
        factor = factor === 7 ? 2 : factor + 1;
    }
    const r = 11 - (suma % 11);
    return limpio.slice(-1) === (r === 11 ? "0" : r === 10 ? "K" : String(r));
}

// Registro de la API -> valores de los inputs
export function aBorrador(r) {
    return {
        document: formatearRut(r.document),
        first_names: r.first_names ?? "",
        last_names: r.last_names ?? "",
        sex: SEXO[r.sex] ?? "M",
        born_date: r.born_date ?? "",
        born_location: r.born_location ?? "",
        document_number: r.document_number ?? "",
    };
    }

// Valores de los inputs -> datos para la API (sin imágenes)
export function aPayload(b) {
    return {
        document: b.document.replace(/[^0-9kK]/g, "").toUpperCase(),
        first_names: b.first_names.trim(),
        last_names: b.last_names.trim(),
        sex: b.sex === "F",
        born_date: b.born_date,
        born_location: b.born_location.trim() || null,
        document_number: String(b.document_number).trim() === "" ? null : Number(b.document_number),
    };
}

export function validar(b) {
    const errores = {};
    if (!b.document.trim()) errores.document = "Obligatorio";
    else if (!rutValido(b.document)) errores.document = "RUT inválido";
    if (!b.first_names.trim()) errores.first_names = "Obligatorio";
    if (!b.last_names.trim()) errores.last_names = "Obligatorio";
    if (!b.born_date) errores.born_date = "Obligatorio";
    else if (b.born_date > new Date().toISOString().slice(0, 10)) errores.born_date = "No puede ser futura";
    if (String(b.document_number).trim() && !/^\d+$/.test(String(b.document_number).trim()))
        errores.document_number = "Solo números";
    return errores;
}

// Errores de DRF {"document": ["RUT Inválido"]} -> {document: "RUT Inválido"}
export function erroresDeApi(e) {
    const porCampo = {};
    for (const [campo, msgs] of Object.entries(e.data || {})) porCampo[campo] = [].concat(msgs).join(" ");
    return Object.keys(porCampo).length ? porCampo : { general: e.message };
}
