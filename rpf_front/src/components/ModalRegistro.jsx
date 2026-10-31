import { useEffect, useRef, useState } from "react";
import { crearRegistro } from "../api";
import { VACIO, aPayload, erroresDeApi, validar } from "../registro";

const FOTOS = [
    { clave: "document_front_picture", etiqueta: "Foto frontal del carnet" },
    { clave: "document_back_picture", etiqueta: "Foto trasera del carnet" },
];

/** Popup con el formulario para registrar a una persona a mano. */
export default function ModalRegistro({ abierto, onCerrar, onCreado }) {
    const dialogRef = useRef(null);
    const [datos, setDatos] = useState(VACIO);
    const [fotos, setFotos] = useState({});
    const [errores, setErrores] = useState({});
    const [guardando, setGuardando] = useState(false);

  // Abrir/cerrar el <dialog> nativo (bloquea el fondo y cierra con Escape)
    useEffect(() => {
        const d = dialogRef.current;
        if (abierto && !d.open) {
            setDatos(VACIO);
            setFotos({});
            setErrores({});
            d.showModal();
            d.querySelector("#nr-document")?.focus();  // el cursor parte en el RUT
        } else if (!abierto && d.open) {
        d.close();
        }
    }, [abierto]);

    const cambiar = (campo) => (e) => {
        setDatos((d) => ({ ...d, [campo]: e.target.value }));
        setErrores((er) => ({ ...er, [campo]: undefined }));
    };

    async function enviar(e) {
        e.preventDefault();
        const locales = validar(datos);
        if (Object.keys(locales).length) return setErrores(locales);

        // multipart/form-data: datos + fotos opcionales
        const fd = new FormData();
        for (const [campo, valor] of Object.entries(aPayload(datos))) {
        if (valor !== null) fd.append(campo, String(valor));
        }
        for (const { clave } of FOTOS) if (fotos[clave]) fd.append(clave, fotos[clave]);

        setGuardando(true);
        try {
            const creado = await crearRegistro(fd);
            onCreado(creado);
            onCerrar();
        } catch (err) {
            setErrores(erroresDeApi(err));
        } finally {
            setGuardando(false);
        }
    }

    const error = (campo) => errores[campo] && <small className="error-campo">{errores[campo]}</small>;
    const props = (campo) => ({
        id: `nr-${campo}`,
        name: campo,
        value: datos[campo],
        onChange: cambiar(campo),
        disabled: guardando,
        className: errores[campo] ? "con-error" : "",
    });

    return (
        <dialog
        ref={dialogRef}
        className="modal"
        onClose={onCerrar}
        onCancel={(e) => guardando && e.preventDefault()}
        onClick={(e) => e.target === dialogRef.current && !guardando && onCerrar()}  // clic fuera
        >
        <form onSubmit={enviar} noValidate>
            <header>
            <h2>Nuevo registro</h2>
            <button type="button" className="cerrar" onClick={onCerrar} disabled={guardando} aria-label="Cerrar">×</button>
            </header>

            <div className="campos">
            <label htmlFor="nr-document">RUT *</label>
            <div>
                <input {...props("document")} placeholder="12.345.678-9" />
                {error("document")}
            </div>

            <label htmlFor="nr-first_names">Nombres *</label>
            <div>
                <input {...props("first_names")} maxLength={350} />
                {error("first_names")}
            </div>

            <label htmlFor="nr-last_names">Apellidos *</label>
            <div>
                <input {...props("last_names")} maxLength={350} />
                {error("last_names")}
            </div>

            <label htmlFor="nr-sex">Sexo *</label>
            <div>
                <select {...props("sex")}>
                <option value="M">Masculino</option>
                <option value="F">Femenino</option>
                </select>
                {error("sex")}
            </div>

            <label htmlFor="nr-born_date">Fecha de nacimiento *</label>
            <div>
                <input {...props("born_date")} type="date" />
                {error("born_date")}
            </div>

            <label htmlFor="nr-born_location">Lugar de nacimiento</label>
            <div>
                <input {...props("born_location")} maxLength={250} />
                {error("born_location")}
            </div>

            <label htmlFor="nr-document_number">N° de documento</label>
            <div>
                <input {...props("document_number")} inputMode="numeric" placeholder="123456789" />
                {error("document_number")}
            </div>

            {FOTOS.map(({ clave, etiqueta }) => (
                <FotoOpcional
                key={clave}
                clave={clave}
                etiqueta={etiqueta}
                archivo={fotos[clave]}
                disabled={guardando}
                error={error(clave)}
                onChange={(f) => setFotos((x) => ({ ...x, [clave]: f }))}
                />
            ))}
            </div>

            {errores.general && <p className="mensaje error">{errores.general}</p>}

            <footer>
            <button type="button" className="secundario" onClick={onCerrar} disabled={guardando}>Cancelar</button>
            <button type="submit" disabled={guardando}>{guardando ? "Guardando…" : "Registrar"}</button>
            </footer>
        </form>
        </dialog>
    );
}

function FotoOpcional({ clave, etiqueta, archivo, disabled, error, onChange }) {
    const [vista, setVista] = useState(null);
    useEffect(() => {
        if (!archivo) return setVista(null);
        const url = URL.createObjectURL(archivo);
        setVista(url);
        return () => URL.revokeObjectURL(url);
    }, [archivo]);

    return (
        <>
        <label htmlFor={`nr-${clave}`}>{etiqueta}</label>
        <div className="foto-opcional">
            <input id={`nr-${clave}`} type="file" accept="image/*" disabled={disabled}
                onChange={(e) => onChange(e.target.files[0] || null)} />
            {vista && <img src={vista} alt={etiqueta} />}
            {error}
        </div>
        </>
    );
}
