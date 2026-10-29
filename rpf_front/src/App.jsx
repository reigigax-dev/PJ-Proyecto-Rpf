import { useEffect, useState } from 'react';
import { eliminarRegistro, listarRegistros } from './api';
import CapturaCarnet from './components/CapturaCarnet';
import './App.css'

function formatearRut(rut) {
  if (!rut) return "";
  const cuerpo = rut.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${cuerpo}-${rut.slice(-1)}`;
}

export default function App() {
  const [registros, setRegistros] = useState([]);
  const [error, setError] = useState("");

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

  async function eliminar(id){
    if (!confirm(`¿Eliminar el registro #${id}?`)) return;
    await eliminarRegistro(id).catch((e) => alert(e.message));
    cargar();
  }

  return (
    <main>
      <h1>Registro con Carnet</h1>
      <p className="ayuda">Posiciona el carnet en el recuadro: primero por el frente y luego por el reverso</p>
    
      <CapturaCarnet onGuardado={cargar} />

      <h2>Registros ({registros.length})</h2>
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
              <tr key={r.id}>
                <td>{r.id}</td>
                <td className="fotos">
                  {r.document_front_picture && <img src={r.document_front_picture} alt="Frente" />}
                  {r.document_back_picture && <img src={r.document_back_picture} alt="Reverso" />}
                </td>
                <td>{formatearRut(r.document)}</td>
                <td>{r.first_names}</td>
                <td>{r.last_names}</td>
                <td>{r.sex ? "M" : "F"}</td>
                <td>{r.born_date}</td>
                <td>{r.born_location || "—"}</td>
                <td>{r.document_number || "—"}</td>
                <td>
                  <button className="secundario" onClick={() => eliminar(r.id)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}
