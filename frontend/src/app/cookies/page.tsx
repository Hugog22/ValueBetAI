import Link from 'next/link';

export default function CookiesPolicy() {
  return (
    <div className="min-h-screen bg-[#FCF9F1] py-12 px-4 sm:px-6 lg:px-8 font-sans text-[#1A1C1E]">
      <div className="max-w-4xl mx-auto bg-white p-8 md:p-12 rounded-[2.5rem] border border-[#E5E7EB] shadow-[0_20px_50px_rgba(0,0,0,0.04)] relative">
        
        {/* Back Button */}
        <Link href="/" className="inline-flex items-center gap-2 text-[#64748B] hover:text-[#064E3B] transition-colors mb-8 group">
          <svg className="w-5 h-5 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span className="text-xs font-bold uppercase tracking-wider">Volver al inicio</span>
        </Link>

        <div className="mb-12">
            <h1 className="text-4xl md:text-5xl font-editorial font-bold text-[#1A1C1E] tracking-tight mb-4">
                Política de <span className="italic font-light">Cookies</span>
            </h1>
            <p className="text-sm text-[#64748B] font-medium uppercase tracking-widest">
                Última actualización: Junio de 2026
            </p>
        </div>

        <div className="prose prose-slate max-w-none text-[#475569] space-y-8">
            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">1. ¿Qué son las Cookies y el Almacenamiento Local?</h2>
                <p>
                    Las cookies son pequeños archivos de texto que los sitios web almacenan en su dispositivo (ordenador, smartphone, tablet) cuando los visita. De manera similar, tecnologías como el "Local Storage" o almacenamiento local permiten a las aplicaciones web guardar datos de forma local en el navegador del usuario. Estas tecnologías son esenciales para el funcionamiento moderno de la web.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">2. Qué tipo de información almacenamos en QuantStake</h2>
                <p>
                    En QuantStake <strong>NO utilizamos cookies publicitarias, ni de rastreo ni de terceros</strong>. Nuestra plataforma tiene un enfoque estricto en la privacidad. 
                </p>
                <p>
                    Únicamente hacemos uso de <strong>tecnologías de almacenamiento estrictamente necesarias (técnicas)</strong> para el funcionamiento básico del servicio y la seguridad de su cuenta. Dado que son estrictamente necesarias, no requieren el consentimiento previo del usuario, pero cumplimos con nuestro deber legal de informarle al respecto.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">3. Detalle de los datos almacenados</h2>
                <div className="overflow-x-auto mt-4">
                    <table className="min-w-full text-sm text-left border-collapse">
                        <thead>
                            <tr className="bg-[#F8F9FA] border-b border-[#E5E7EB]">
                                <th className="px-4 py-3 font-bold text-[#1A1C1E]">Nombre</th>
                                <th className="px-4 py-3 font-bold text-[#1A1C1E]">Tipo</th>
                                <th className="px-4 py-3 font-bold text-[#1A1C1E]">Finalidad</th>
                                <th className="px-4 py-3 font-bold text-[#1A1C1E]">Duración</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr className="border-b border-[#E5E7EB]">
                                <td className="px-4 py-3 font-medium">auth_token</td>
                                <td className="px-4 py-3">Local Storage</td>
                                <td className="px-4 py-3">Almacena el token de acceso cifrado (JWT) necesario para mantener la sesión abierta del usuario en la plataforma de manera segura, evitando que tenga que iniciar sesión en cada recarga de página.</td>
                                <td className="px-4 py-3">Persistente (hasta que se cierre la sesión manualmente)</td>
                            </tr>
                            <tr className="border-b border-[#E5E7EB]">
                                <td className="px-4 py-3 font-medium">cookie_consent</td>
                                <td className="px-4 py-3">Local Storage</td>
                                <td className="px-4 py-3">Guarda la preferencia del usuario sobre si ya ha leído y aceptado el aviso informativo del banner de cookies, para no volver a mostrarlo.</td>
                                <td className="px-4 py-3">Persistente</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">4. Cómo gestionar o eliminar esta información</h2>
                <p>
                    Dado que solo utilizamos almacenamiento esencial para el servicio, si bloquea el uso de Local Storage en su navegador, <strong>no podrá iniciar sesión ni utilizar las funciones de la plataforma</strong>.
                </p>
                <p>
                    Sin embargo, puede eliminar estos datos en cualquier momento:
                </p>
                <ul className="list-disc pl-6 space-y-2">
                    <li>Al hacer clic en "Cerrar sesión" dentro de su panel de usuario de QuantStake, el sistema eliminará automáticamente su <code>auth_token</code>.</li>
                    <li>Puede usar las herramientas de desarrollador o las opciones de privacidad de su navegador para borrar los datos del sitio y las cookies manualmente.</li>
                </ul>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">5. Actualizaciones de esta política</h2>
                <p>
                    Si en el futuro QuantStake decide incorporar servicios de analítica (como Google Analytics) o cualquier otra tecnología de rastreo, esta política será actualizada y se solicitará previamente su consentimiento expreso mediante un sistema de gestión de cookies avanzado.
                </p>
            </section>
        </div>

        <div className="mt-16 pt-8 border-t border-[#E5E7EB] text-center">
            <p className="text-[#94A3B8] text-[9px] uppercase tracking-[0.4em] font-medium">
                Sistemas de Inversión QuantStake &copy; 2026
            </p>
        </div>
      </div>
    </div>
  );
}
