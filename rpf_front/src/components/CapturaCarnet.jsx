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

export default function CapturaCarnet({ onGuardado }) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const formRef = useRef(null);

    const [fotos, setFotos] = useState([]);
    const [modo, setModo] = useState("manual");
    const [segundos, setSegundos] = useState(4);
    const [cuenta, setCuenta] = useState(null);
    const [procesando, setProcesando] = useState(false);
    const [mensaje, setMensaje] = useState({tipo: "", texto: "" });
    const [formulario, setFormulario] = useState(FORMULARIO_VACIO)

    const ladoActual = LADOS[fotos.length];

    useEffect(() => {
        let stream;
        navigator.mediaDevices
            .getUserMedia({ video: { width: { ideal: 1920 }, height: { ideal: 1080 }}, audio: false})
            .then((s) => {
                stream = s;
                if (videoRef.current) videoRef.current.srcObject = s;
            })
            .catch((e) => setMensaje({ tipo: "error", texto: "No se pudo abrir la cámara: " + e.message }));
        return () => stream?.getTracks().forEach((t) => t.stop());
    }, []);

    const capturar = useCallback(() => {
        const video = videoRef.current; 
        const canvas = canvasRef.current;
        if (!video?.videoWidth) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        canvas.toBlob(
            (blob) => 
                setFotos((prev) =>
                    prev.length >= LADOS.length ? prev : [...prev, { blob, url: URL.createObjectURL(blob) }]
                ),
            "image/jpeg",
            0.95
        );
    }, []);

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

            if (detectado.faltantes.length) {
                const faltan = detectado.faltantes.map((c) => NOMBRES_CAMPOS[c] || c).join(", ");
                throw new Error(`No se pudo leer: ${faltan}. Repite las fotos con mejor luz y el carnet mas cerca`);
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

            setMensaje({ tipo: "info", texto: "Guardando registro…"});
            const fd = new FormData(formRef.current);
            for (const [campo, valor] of [...fd.entries()]) if (valor === "") fd.delete(campo);
            const guardado = await crearRegistro(agregarFotos(fd));

            setMensaje({
                tipo: "ok",
                texto: `Registro #${guardado.id} guardado: ${guardado.first_names} ${guardado.last_names}`,
            });
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

    return (
        <section className="captura">
            <div className="visor">
                <video ref={videoRef} autoPlay playsInline muted />
                <div className="marco" />
                {ladoActual && !procesando && <div className="indicacion">{ladoActual.etiqueta}</div>}
                {cuenta !== null && <div className="cuenta">{cuenta}</div>}
            </div>
            <canvas ref={canvasRef} hidden />

            <div className="controles">
                <label>
                    <input type="radio" checked={modo === "manual"} disabled={procesando} 
                            onChange={() => setModo("manual")}/> Manual
                </label>
                <label>
                    <input type="radio" checked={modo === "automatico"} disabled={procesando}
                            onChange={() => setModo("automatico")}/> Automatico, cada
                    <input type="number" min="2" max="15" value={segundos}
                            onChange={(e) => setSegundos(Number(e.target.value) || 2)}/> s
                </label>

                {modo === "manual" && ladoActual && (
                    <button onClick={capturar} disabled={procesando}>
                        Capturar {ladoActual.etiqueta.toLowerCase()}
                    </button>
                )}
                {fotos.length > 0 && !procesando && (
                    <button className="secundario" onClick={reiniciar}>
                        Repetir
                    </button>
                )}
            </div>

            <div className="miniaturas">
                {LADOS.map((lado, i) => (
                    <figure key={lado.clave}>
                        {fotos[i] ? <img src={fotos[i].url} alt={lado.etiqueta} /> : <div className="vacio"/>}
                    <figcaption>{lado.etiqueta}</figcaption>
                    </figure>
                ))}
            </div>

            {mensaje.texto && <p className={`mensaje ${mensaje.tipo}`}>{mensaje.texto}</p>}
            
            
            <form ref={formRef} hidden aria-hidden="true" onSubmit={(e) => e.preventDefault()}>
                {Object.entries(formulario).map(([campo, valor]) => (
                    <input key={campo} name={campo} value={valor} readOnly/>
                ))}
            </form>
        </section>
    );
}
