export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

function headers() {
    const token = localStorage.getItem("access");
    return token ? {Authorization: `Bearer ${token}` } : {};
}

async function manejar(resp) {
    const data = resp.status === 204 ? null : await resp.json().catch(() => null);
    if (!resp.ok) {
        const error = new Error(formatearError(data) || `Error ${resp.status}`);
        error.data = data;
        throw error;
    }
    return data;
}

function formatearError(data){
    if(!data) return "";
    if(data.detail) return data.detail;
    return Object.entries(data)
        .map(([campo, msgs]) => `${campo}: ${[].concat(msgs).join(" ")}`)
        .join(" | ");
}

export const listarRegistros = () =>
    fetch(`${API}signup/list/`, { headers: headers() }).then(manejar);

export const escanearCarnet = (formData) =>
    fetch(`${API}signup/scan/`, { method: "POST", body: formData, headers: headers() }).then(manejar);

export const crearRegistro = (formData) =>
    fetch(`${API}signup/add/`, { method: "POST", body: formData, headers: headers() }).then(manejar);

export const eliminarRegistro = (id) =>
    fetch(`${API}signup/delete/${id}/`, { method: "DELETE", headers: headers() }).then(manejar);
