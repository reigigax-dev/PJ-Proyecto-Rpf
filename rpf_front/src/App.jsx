import { useEffect, useState } from "react";
import { descargarExcel, eliminarRegistro, listarRegistros } from "./api";
import CapturaCarnet from "./components/CapturaCarnet";
import FilaRegistro from "./components/FilaRegistro";
import ModalRegistro from "./components/ModalRegistro";
import "./App.css";

export default function App() {
  const [registros, setRegistros] = useState([]);
  const [error, setError] = useState("");
  const [descargando, setDescargando] = useState(false);
  const [modalAbierto, setModalAbierto] = useState(false);

  const cargar = () =>
    listarRegistros()
      .then((data) => {
        setRegistros(data);
        setError("");
      })
      .catch((e) => setError("No se pudo cargar la lista: " + e.message));

  useEffect(() => {
    cargar();
  }, []);

  // Reemplaza solo la fila editada, sin recargar toda la tabla
  const actualizar = (nuevo) =>
    setRegistros((lista) => lista.map((r) => (r.id === nuevo.id ? nuevo : r)));

  async function eliminar(id) {
    if (!confirm(`¿Eliminar el registro #${id} y sus fotos?`)) return;
    try {
      await eliminarRegistro(id);
      setRegistros((lista) => lista.filter((r) => r.id !== id));
    } catch (e) {
      setError(e.message);
    }
  }

  async function exportar() {
    setDescargando(true);
    try {
      await descargarExcel();
    } catch (e) {
      setError(e.message);
    } finally {
      setDescargando(false);
    }
  }

  return (
    <main>
      <h1>Registro con carnet</h1>
      <p className="ayuda">Muestra el carnet a la cámara: primero el frente y luego el reverso.</p>

      <CapturaCarnet onGuardado={cargar} />

      <div className="encabezado-tabla">
        <h2>Registros ({registros.length})</h2>
        <div className="botones">
          <button onClick={() => setModalAbierto(true)}>+ Nuevo registro</button>
          <button className="secundario" onClick={exportar} disabled={descargando || registros.length === 0}>
            {descargando ? "Generando…" : "Descargar Excel"}
          </button>
        </div>
      </div>
      {error && <p className="mensaje error">{error}</p>}
      <div className="tabla">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Carnet</th><th>RUT</th><th>Nombres</th><th>Apellidos</th>
              <th>Sexo</th><th>Nacimiento</th><th>Lugar</th><th>N° doc.</th><th></th>
            </tr>
          </thead>
          <tbody>
            {registros.map((r) => (
              <FilaRegistro key={r.id} registro={r} onActualizado={actualizar} onEliminar={eliminar} />
            ))}
          </tbody>
        </table>
      </div>

      <ModalRegistro
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        onCreado={(nuevo) => setRegistros((lista) => [...lista, nuevo])}
      />
    </main>
  );
}
