import { useState } from "react";
import { editarRegistro } from "../api";
import { SEXO, aBorrador, aPayload, erroresDeApi, formatearRut, validar } from "../registro";

export default function FilaRegistro({ registro: r, onActualizado, onEliminar }) {
    const [editando, setEditando] = useState(false);
    const [borrador, setBorrador] = useState(null);
    const [errores, setErrores] = useState({});
    const [guardando, setGuardando] = useState(false);

    function empezar() {
        setBorrador(aBorrador(r));
        setErrores({});
        setEditando(true);
    }

    function cancelar() {
        setEditando(false);
        setBorrador(null);
        setErrores({});
    }

    async function guardar() {
        const locales = validar(borrador);
        if (Object.keys(locales).length) return setErrores(locales);
        setGuardando(true);
        try {
            const actualizado = await editarRegistro(r.id, aPayload(borrador));
            onActualizado(actualizado);
            cancelar();
        } catch (e) {
            setErrores(erroresDeApi(e));
        } finally {
            setGuardando(false);
        }
    }

    const cambiar = (campo) => (e) => setBorrador((b) => ({ ...b, [campo]: e.target.value }));
    const teclas = (e) => {
        if (e.key === "Enter") guardar();
        if (e.key === "Escape") cancelar();
    };

    const fotos = (
        <td className="fotos">
            {r.document_front_picture && <img src={r.document_front_picture} alt="Frente" />}
            {r.document_back_picture && <img src={r.document_back_picture} alt="Reverso" />}
        </td>
    );

    if (!editando) {
        return (
        <tr>
            <td>{r.id}</td>
            {fotos}
            <td>{formatearRut(r.document)}</td>
            <td>{r.first_names}</td>
            <td>{r.last_names}</td>
            <td>{SEXO[r.sex]}</td>
            <td>{r.born_date}</td>
            <td>{r.born_location || "—"}</td>
            <td>{r.document_number || "—"}</td>
            <td className="acciones">
                <button onClick={empezar}>Editar</button>
                <button className="secundario" onClick={() => onEliminar(r.id)}>Eliminar</button>
            </td>
        </tr>
        );
    }

    const campo = (nombre, input) => (
        <td>
            {input}
            {errores[nombre] && <small className="error-campo">{errores[nombre]}</small>}
        </td>
    );
    const props = (nombre) => ({
        name: nombre,
        value: borrador[nombre],
        onChange: cambiar(nombre),
        onKeyDown: teclas,
        disabled: guardando,
        className: errores[nombre] ? "con-error" : "",
    });

    return (
        <tr className="editando">
        <td>{r.id}</td>
        {fotos}
        {campo("document", <input {...props("document")} placeholder="12.345.678-9" size={12} autoFocus />)}
        {campo("first_names", <input {...props("first_names")} maxLength={350} />)}
        {campo("last_names", <input {...props("last_names")} maxLength={350} />)}
        {campo("sex",
            <select {...props("sex")}>
                <option value="M">M</option>
                <option value="F">F</option>
            </select>
        )}
        {campo("born_date", <input {...props("born_date")} type="date" />)}
        {campo("born_location", <input {...props("born_location")} maxLength={250} />)}
        {campo("document_number", <input {...props("document_number")} inputMode="numeric" size={10} />)}
        <td className="acciones">
            <button onClick={guardar} disabled={guardando}>{guardando ? "Guardando…" : "Guardar"}</button>
            <button className="secundario" onClick={cancelar} disabled={guardando}>Cancelar</button>
            {errores.general && <small className="error-campo">{errores.general}</small>}
        </td>
        </tr>
    );
}
