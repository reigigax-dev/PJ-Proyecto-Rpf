import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { crearRegistro, escanearCarnet } from "../api";

const LADOS = [
    { clave: "document_front_picture", etiqueta: "Parte frontal del carnet" },
    { clave: "document_back_picture", etiqueta: "Parte trasera del carnet" },
];

const FORMULARIO_VACIO = {
    document: "",
    first_names: "",
    last_names: "",
    sex: "",
    born_date: "",
    born_location: "",
    document_number: "",
};

const NOMBRES_CAMPOS = {
    document: "RUT",
    first_names: "Nombres",
    last_names: "Apellidos",
    sex: "Sexo",
    born_date: "Fecha de nacimiento",
};

const CUADROS_POR_FOTO = 6;
const MARGEN_RECORTE = 0.12;

function nitidez(ctx, w, h) {
    const { data } = ctx.getImageData(0, 0, w, h);
    const gris = new Float32Array(w * h);
    for (let i = 0; i < w * h; i++) gris[i] = data[i * 4] * 0.299 + data[i * 4 + 1] * 0.587 + data[i * 4 + 2] * 0.114;
    let suma = 0, suma2 = 0, n = 0;
    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            const i = y * w + x;
            const lap = gris[i - w] + gris[i + w] + gris[i - 1] + gris[i + 1] - 4 * gris[i];
            suma += lap; suma2 += lap * lap; n++;
        }
    }
    const media = suma / n;
    return suma2 / n - media * media;
}

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export default function CapturaCarnet({ onGuardado }) {
    const videoRef = useRef(null);
    const marcoRef = useRef(null);
    const formRef = useRef(null);

    const [fotos, setFotos] = useState([]);
    const [modo, setModo] = useState("manual");
    const [segundos, setSegundos] = useState(4);
    const [cuenta, setCuenta] = useState(null);
    const [capturando, setCapturando] = useState(false);
    const [procesando, setProcesando] = useState(false);
    const [mensaje, setMensaje] = useState({ tipo: "", texto: "" });
    const [formulario, setFormulario] = useState(FORMULARIO_VACIO);

    const ladoActual = LADOS[fotos.length];

    useEffect(() => {
        let stream;
        navigator.mediaDevices
        .getUserMedia({
            video: { width: { ideal: 1920 }, height: { ideal: 1080 }, facingMode: "environment" },
            audio: false,
        })
        .then(async (s) => {
            stream = s;
            if (videoRef.current) videoRef.current.srcObject = s;
            const track = s.getVideoTracks()[0];
            const caps = track.getCapabilities?.() || {};
            if (caps.focusMode?.includes("continuous")) {
                await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] }).catch(() => {});
            }
            const { width, height } = track.getSettings();
            if (width < 1280) {
                setMensaje({ tipo: "info", texto: `La cámara entrega solo ${width}x${height}. Acerca bien el carnet a la guía.` });
            }
        })
        .catch((e) => setMensaje({ tipo: "error", texto: "No se pudo abrir la cámara: " + e.message }));
        return () => stream?.getTracks().forEach((t) => t.stop());
    }, []);

    const zonaRecorte = useCallback(() => {
        const video = videoRef.current;
        const vw = video.videoWidth, vh = video.videoHeight;
        const caja = video.getBoundingClientRect();
        const marco = marcoRef.current.getBoundingClientRect();
        const escala = Math.max(caja.width / vw, caja.height / vh);
        const offX = (caja.width - vw * escala) / 2;
        const offY = (caja.height - vh * escala) / 2;
        let x = (marco.left - caja.left - offX) / escala;
        let y = (marco.top - caja.top - offY) / escala;
        let w = marco.width / escala;
        let h = marco.height / escala;
        x -= w * MARGEN_RECORTE; y -= h * MARGEN_RECORTE;
        w *= 1 + 2 * MARGEN_RECORTE; h *= 1 + 2 * MARGEN_RECORTE;
        x = Math.max(0, x); y = Math.max(0, y);
        return { x, y, w: Math.min(w, vw - x), h: Math.min(h, vh - y) };
    }, []);

    const capturar = useCallback(async () => {
        const video = videoRef.current;
        if (!video?.videoWidth || capturando) return;
        setCapturando(true);
        try {
            const z = zonaRecorte();
            const lienzo = document.createElement("canvas");
            lienzo.width = Math.round(z.w);
            lienzo.height = Math.round(z.h);
            const ctx = lienzo.getContext("2d", { willReadFrequently: true });
            const muestra = document.createElement("canvas");
            muestra.width = 400;
            muestra.height = Math.round((400 * z.h) / z.w);
            const ctxMuestra = muestra.getContext("2d", { willReadFrequently: true });

            let mejor = { puntaje: -1, blob: null };
            for (let i = 0; i < CUADROS_POR_FOTO; i++) {
                ctx.drawImage(video, z.x, z.y, z.w, z.h, 0, 0, lienzo.width, lienzo.height);
                ctxMuestra.drawImage(lienzo, 0, 0, muestra.width, muestra.height);
                const puntaje = nitidez(ctxMuestra, muestra.width, muestra.height);
                if (puntaje > mejor.puntaje) {
                    const blob = await new Promise((r) => lienzo.toBlob(r, "image/jpeg", 0.95));
                    mejor = { puntaje, blob };
                }
                await esperar(120);
            }
            setFotos((prev) =>
                prev.length >= LADOS.length ? prev : [...prev, { blob: mejor.blob, url: URL.createObjectURL(mejor.blob) }]
            );
        } finally {
            setCapturando(false);
        }
    }, [capturando, zonaRecorte]);

    useEffect(() => {
        if (modo !== "automatico" || procesando || fotos.length >= LADOS.length) {
            setCuenta(null);
            return;
        }
        setCuenta(segundos);
        const id = setInterval(() => setCuenta((c) => (c > 0 ? c - 1 : c)), 1000);
        return () => clearInterval(id);
    }, [modo, procesando, fotos.length, segundos]);

    useEffect(() => {
        if (cuenta === 0) {
            setCuenta(null);
            capturar();
        }
    }, [cuenta, capturar]);

    useEffect(() => {
        if (fotos.length === LADOS.length && !procesando) procesar();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [fotos]);

    function agregarFotos(fd) {
        LADOS.forEach((lado, i) => fd.append(lado.clave, fotos[i].blob, `${lado.clave}.jpg`));
        return fd;
    }

    async function procesar() {
        setProcesando(true);
        try {
            setMensaje({ tipo: "info", texto: "Leyendo el carnet…" });
            const detectado = await escanearCarnet(agregarFotos(new FormData()));

            if (detectado.missing_data?.length) {
                const faltan = detectado.missing_data.map((c) => NOMBRES_CAMPOS[c] || c).join(", ");
                throw new Error(`No se pudo leer: ${faltan}. Repite las fotos con mejor luz, sin reflejos y con el carnet dentro de la guía.`);
            }

            flushSync(() =>
                setFormulario({
                    document: detectado.document ?? "",
                    first_names: detectado.first_names ?? "",
                    last_names: detectado.last_names ?? "",
                    sex: detectado.sex === null ? "" : String(detectado.sex),
                    born_date: detectado.born_date ?? "",
                    born_location: detectado.born_location ?? "",
                    document_number: detectado.document_number ?? "",
                })
            );

            setMensaje({ tipo: "info", texto: "Guardando registro…" });
            const fd = new FormData(formRef.current);
            for (const [campo, valor] of [...fd.entries()]) if (valor === "") fd.delete(campo);
            const guardado = await crearRegistro(agregarFotos(fd));

            setMensaje({ tipo: "ok", texto: `Registro #${guardado.id} guardado: ${guardado.first_names} ${guardado.last_names}` });
            onGuardado?.(guardado);
        } catch (e) {
            setMensaje({ tipo: "error", texto: e.message });
        } finally {
            reiniciar();
            setProcesando(false);
        }
    }

    function reiniciar() {
        setFotos((prev) => {
            prev.forEach((f) => URL.revokeObjectURL(f.url));
            return [];
        });
        setFormulario(FORMULARIO_VACIO);
        if (modo === "automatico") setModo("manual");
    }

    const ocupado = procesando || capturando;

    return (
        <section className="captura">
            <div className="visor">
                <video ref={videoRef} autoPlay playsInline muted />
                <div className="marco" ref={marcoRef} />
                {ladoActual && !procesando && (
                    <div className="indicacion">{capturando ? "Quieto… enfocando" : ladoActual.etiqueta}</div>
                )}
                {cuenta !== null && <div className="cuenta">{cuenta}</div>}
            </div>

            <div className="controles">
                <label>
                    <input type="radio" checked={modo === "manual"} disabled={ocupado}
                            onChange={() => setModo("manual")} /> Manual
                </label>
                <label>
                    <input type="radio" checked={modo === "automatico"} disabled={ocupado}
                            onChange={() => setModo("automatico")} /> Automático, cada
                    <input type="number" min="2" max="15" value={segundos}
                            onChange={(e) => setSegundos(Number(e.target.value) || 2)} /> s
                </label>

                {modo === "manual" && ladoActual && (
                    <button onClick={capturar} disabled={ocupado}>
                        Capturar {ladoActual.etiqueta.toLowerCase()}
                    </button>
                )}
                {fotos.length > 0 && !ocupado && (
                    <button className="secundario" onClick={reiniciar}>Repetir</button>
                )}
            </div>

            <div className="miniaturas">
                {LADOS.map((lado, i) => (
                <figure key={lado.clave}>
                    {fotos[i] ? <img src={fotos[i].url} alt={lado.etiqueta} /> : <div className="vacio" />}
                    <figcaption>{lado.etiqueta}</figcaption>
                </figure>
                ))}
            </div>

            {mensaje.texto && <p className={`mensaje ${mensaje.tipo}`}>{mensaje.texto}</p>}

            <form ref={formRef} hidden aria-hidden="true" onSubmit={(e) => e.preventDefault()}>
                {Object.entries(formulario).map(([campo, valor]) => (
                <input key={campo} name={campo} value={valor} readOnly />
                ))}
            </form>
        </section>
    );
}
