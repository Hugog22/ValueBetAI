"use client";

import { useEffect, useState } from "react";
import Navbar from "../../components/Navbar";

interface TeamCharacteristic {
  team_id: number;
  team_name: string;
  offensive_strength: number;
  defensive_solidity: number;
  motivation: number;
  momentum: number;
}

export default function AdminDashboard() {
  const [characteristics, setCharacteristics] = useState<TeamCharacteristic[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchCharacteristics();
  }, []);

  const fetchCharacteristics = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/proxy/admin/team-characteristics", {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Error fetching characteristics or unauthorized");
      const data = await res.json();
      setCharacteristics(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/proxy/admin/team-characteristics", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ characteristics })
      });
      if (!res.ok) throw new Error("Error saving characteristics");
      setSuccess("Características actualizadas y aplicadas al modelo predictivo.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (teamId: number, field: keyof TeamCharacteristic, value: number) => {
    setCharacteristics(prev => 
      prev.map(team => 
        team.team_id === teamId ? { ...team, [field]: value } : team
      )
    );
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-6xl w-full mx-auto p-4 md:p-8 pt-24">
        <h1 className="text-4xl font-black uppercase text-orange-500 mb-2">Panel de Administración</h1>
        <p className="text-gray-400 mb-8 text-lg font-light">
          Ajusta manualmente el nivel de cada equipo de LaLiga. 
          <br/>
          <span className="text-white font-bold">Nota:</span> Estos valores tienen un alto peso en el modelo predictivo, sobreescribiendo el historial reciente.
        </p>

        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-xl mb-6">
            Error: {error}
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-2xl">
            {success && (
              <div className="bg-green-900/50 border-b border-green-500 text-green-200 p-4 font-medium flex items-center gap-2">
                ✅ {success}
              </div>
            )}
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-gray-800/80 text-gray-300 uppercase text-xs font-bold tracking-wider">
                  <tr>
                    <th className="p-4 border-b border-gray-700">Equipo</th>
                    <th className="p-4 border-b border-gray-700">Fuerza Ofensiva (1-10)</th>
                    <th className="p-4 border-b border-gray-700">Solidez Defensiva (1-10)</th>
                    <th className="p-4 border-b border-gray-700">Motivación (1-10)</th>
                    <th className="p-4 border-b border-gray-700">Momentum (1-10)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {characteristics.map(team => (
                    <tr key={team.team_id} className="hover:bg-gray-800/40 transition-colors">
                      <td className="p-4 font-medium text-white">{team.team_name}</td>
                      
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <input 
                            type="range" min="1" max="10" step="0.5" 
                            value={team.offensive_strength}
                            onChange={(e) => handleChange(team.team_id, "offensive_strength", parseFloat(e.target.value))}
                            className="w-full accent-orange-500 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="w-8 text-center text-orange-400 font-mono bg-gray-950 rounded px-1">{team.offensive_strength}</span>
                        </div>
                      </td>

                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <input 
                            type="range" min="1" max="10" step="0.5" 
                            value={team.defensive_solidity}
                            onChange={(e) => handleChange(team.team_id, "defensive_solidity", parseFloat(e.target.value))}
                            className="w-full accent-orange-500 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="w-8 text-center text-orange-400 font-mono bg-gray-950 rounded px-1">{team.defensive_solidity}</span>
                        </div>
                      </td>

                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <input 
                            type="range" min="1" max="10" step="0.5" 
                            value={team.motivation}
                            onChange={(e) => handleChange(team.team_id, "motivation", parseFloat(e.target.value))}
                            className="w-full accent-orange-500 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="w-8 text-center text-orange-400 font-mono bg-gray-950 rounded px-1">{team.motivation}</span>
                        </div>
                      </td>

                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <input 
                            type="range" min="1" max="10" step="0.5" 
                            value={team.momentum}
                            onChange={(e) => handleChange(team.team_id, "momentum", parseFloat(e.target.value))}
                            className="w-full accent-orange-500 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="w-8 text-center text-orange-400 font-mono bg-gray-950 rounded px-1">{team.momentum}</span>
                        </div>
                      </td>

                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-6 bg-gray-800/80 border-t border-gray-700 flex justify-end">
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-orange-600 hover:bg-orange-500 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg shadow-orange-600/20 active:scale-95 disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? "Guardando..." : "Guardar Cambios"}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
