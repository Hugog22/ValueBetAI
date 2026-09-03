import React from 'react';

export default function PrivacidadPage() {
    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-900 py-20 px-6 font-sans">
            <div className="max-w-3xl mx-auto">
                <h1 className="text-4xl font-editorial font-bold mb-8 text-[#1B365D]">Política de Privacidad</h1>
                <p className="text-[#94a3b8] mb-8 text-sm">Última actualización: 20 de Junio de 2026</p>

                <div className="space-y-8 text-[#cbd5e1] leading-relaxed text-sm">
                    
                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">1. Información General</h2>
                        <p>
                            En QuantStake ("nosotros", "nuestro"), respetamos tu privacidad y estamos comprometidos a proteger tus datos personales. Esta Política de Privacidad te informa sobre cómo recopilamos, usamos, almacenamos y compartimos tus datos cuando utilizas nuestra plataforma, de acuerdo con el Reglamento General de Protección de Datos (RGPD) de la Unión Europea y otras leyes aplicables.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">2. Datos que Recopilamos</h2>
                        <p className="mb-2">Recopilamos los siguientes tipos de datos personales cuando te registras y utilizas nuestra plataforma:</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li><strong>Datos de Identidad y Contacto:</strong> Dirección de correo electrónico y contraseña encriptada.</li>
                            <li><strong>Datos Financieros:</strong> Procesamos tus pagos a través de proveedores externos seguros (como Stripe). Nosotros no almacenamos los números de tu tarjeta de crédito ni tu información bancaria.</li>
                            <li><strong>Datos Técnicos y de Uso:</strong> Dirección IP, tipo de navegador, información sobre tu dispositivo, páginas visitadas y el tiempo que pasas en nuestra plataforma.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">3. Cómo Usamos tus Datos</h2>
                        <p className="mb-2">Tus datos personales se utilizan para las siguientes finalidades:</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>Proporcionarte acceso y mantener tu cuenta en la plataforma de QuantStake.</li>
                            <li>Procesar tus pagos y gestionar tu suscripción o periodo de prueba.</li>
                            <li>Enviarte notificaciones importantes sobre el servicio (por ejemplo, cambios en tus pagos o problemas de seguridad).</li>
                            <li>Mejorar nuestros algoritmos y la experiencia de usuario analizando métricas de uso anónimas.</li>
                            <li>Prevenir el fraude y garantizar la seguridad de nuestra plataforma.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">4. Compartir tus Datos</h2>
                        <p>
                            No vendemos tus datos personales a terceros. Solo compartimos tus datos con proveedores de servicios de confianza necesarios para operar nuestra plataforma (por ejemplo, pasarelas de pago como Stripe o servicios de envío de correos transaccionales). Exigimos a todos los terceros que respeten la seguridad de tus datos y los traten conforme a la ley.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">5. Retención de Datos</h2>
                        <p>
                            Conservaremos tus datos personales solo durante el tiempo necesario para cumplir con los fines para los que los recopilamos, lo que incluye satisfacer cualquier requisito legal, contable o de presentación de informes. Si decides eliminar tu cuenta, borraremos tus datos personales de nuestros servidores, a menos que la ley nos exija retener cierta información.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">6. Seguridad de los Datos</h2>
                        <p>
                            Hemos implementado medidas de seguridad técnicas y organizativas adecuadas para evitar que tus datos personales se pierdan accidentalmente, se utilicen o se acceda a ellos de forma no autorizada, se modifiquen o se divulguen. Tus contraseñas se almacenan mediante algoritmos de cifrado fuertes y todo el tráfico viaja a través de conexiones seguras (HTTPS).
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">7. Tus Derechos Legales (RGPD)</h2>
                        <p className="mb-2">Bajo las leyes de protección de datos, tienes derecho a:</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>Solicitar el acceso a tus datos personales.</li>
                            <li>Solicitar la corrección de los datos que tenemos sobre ti.</li>
                            <li>Solicitar el borrado de tus datos personales ("derecho al olvido").</li>
                            <li>Oponerte o solicitar la restricción del tratamiento de tus datos.</li>
                            <li>Solicitar la transferencia (portabilidad) de tus datos personales.</li>
                            <li>Retirar tu consentimiento en cualquier momento.</li>
                        </ul>
                        <p className="mt-4">
                            Para ejercer cualquiera de estos derechos, por favor contáctanos directamente a través del correo de soporte.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-slate-900 mb-4">8. Contacto</h2>
                        <p>
                            Si tienes alguna pregunta sobre esta Política de Privacidad o sobre nuestras prácticas de protección de datos, por favor contáctanos en: <strong>quantstake@outlook.es</strong>
                        </p>
                    </section>

                </div>

                <div className="mt-12 pt-8 border-t border-white/10 flex justify-center">
                    <a href="/" className="text-[#1B365D] hover:text-slate-900 transition-colors text-sm font-bold uppercase tracking-wider">
                        ← Volver a Inicio
                    </a>
                </div>
            </div>
        </div>
    );
}
