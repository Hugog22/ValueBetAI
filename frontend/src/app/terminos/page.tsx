import Link from 'next/link';

export default function TermsAndConditions() {
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
                Términos y <span className="italic font-light">Condiciones</span>
            </h1>
            <p className="text-sm text-[#64748B] font-medium uppercase tracking-widest">
                Última actualización: Junio de 2026
            </p>
        </div>

        <div className="prose prose-slate max-w-none text-[#475569] space-y-8">
            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">1. Naturaleza del Servicio</h2>
                <p>
                    QuantStake es una plataforma de análisis estadístico impulsada por inteligencia artificial. Nuestro servicio consiste en proporcionar predicciones, cálculos de probabilidades ("value bets") y análisis de datos relacionados con eventos deportivos (principalmente fútbol). 
                    <strong>QuantStake NO es una casa de apuestas</strong>, no organiza juegos de azar, ni capta fondos para realizar apuestas en nombre de terceros. Somos exclusivamente un proveedor de información y software analítico.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">2. Mayoría de Edad y Jurisdicción</h2>
                <p>
                    El uso de QuantStake está estrictamente reservado a personas mayores de dieciocho (18) años o la edad legal para participar en actividades de apuestas en su jurisdicción de residencia. Al registrarse, usted declara y garantiza bajo su propia responsabilidad que cumple con este requisito. El acceso al servicio puede estar restringido en aquellos países donde la promoción de herramientas para apuestas no esté permitida.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">3. Riesgos y Exención de Responsabilidad</h2>
                <p className="font-medium text-red-600">
                    LAS APUESTAS DEPORTIVAS CONLLEVAN UN ALTO RIESGO DE PÉRDIDA FINANCIERA.
                </p>
                <p>
                    Toda la información proporcionada por nuestro algoritmo (incluyendo pero no limitado a: predicciones, cuotas estimadas, "value bets", "edge" o "ROI esperado") tiene fines puramente informativos y analíticos. 
                    <strong>QuantStake no garantiza ganancias económicas de ningún tipo.</strong> Las rentabilidades pasadas o mostradas en la plataforma ("Rendimiento del último trimestre") se basan en simulaciones o históricos y no son indicadores fiables de resultados futuros.
                </p>
                <p>
                    El usuario es el único y exclusivo responsable de cualquier decisión de apuesta que realice basándose en la información proporcionada por nuestra plataforma. QuantStake y sus creadores, afiliados o empleados no asumen ninguna responsabilidad por pérdidas directas, indirectas, incidentales o consecuentes que resulten del uso de nuestra herramienta.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">4. Condiciones de Suscripción y Pagos</h2>
                <p>
                    El acceso a las funcionalidades "Pro" de QuantStake requiere una suscripción mensual. El pago se procesa de forma segura a través de nuestro proveedor (Stripe).
                </p>
                <ul className="list-disc pl-6 space-y-2">
                    <li>La suscripción se renueva automáticamente cada mes al precio fijado en el momento de la contratación.</li>
                    <li>Puede cancelar su suscripción en cualquier momento desde los ajustes de su cuenta. No exigimos permanencia.</li>
                    <li>La cancelación será efectiva al finalizar el período de facturación en curso. No se realizarán reembolsos parciales por períodos no completados.</li>
                </ul>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">5. Propiedad Intelectual</h2>
                <p>
                    Todo el contenido, algoritmos, modelos de IA, bases de datos, código fuente, diseño, logotipos y textos alojados en QuantStake son propiedad exclusiva de los creadores de la plataforma. 
                    Está terminantemente prohibido extraer, copiar, distribuir, raspar (scraping) o revender las predicciones y cuotas proporcionadas por QuantStake sin autorización expresa y por escrito.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">6. Modificaciones del Servicio</h2>
                <p>
                    QuantStake se reserva el derecho de modificar, suspender o discontinuar cualquier parte del servicio (incluyendo ligas analizadas o umbrales de detección) en cualquier momento. De igual manera, nos reservamos el derecho de actualizar estos Términos y Condiciones, notificando a los usuarios registrados mediante la plataforma o vía correo electrónico.
                </p>
            </section>

            <section>
                <h2 className="text-2xl font-bold text-[#1A1C1E] mb-4">7. Juego Responsable</h2>
                <p>
                    Recomendamos encarecidamente utilizar las apuestas deportivas como una forma de entretenimiento y no como una fuente principal de ingresos. Si siente que tiene problemas con el juego, le instamos a buscar ayuda en organizaciones especializadas en su país (ej. JugarBIEN en España).
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
