export const COUNTRY_FLAGS: Record<string, string> = {
  Argentina: '🇦🇷', France: '🇫🇷', Spain: '🇪🇸', England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  Brazil: '🇧🇷', Portugal: '🇵🇹', Belgium: '🇧🇪', Netherlands: '🇳🇱',
  Germany: '🇩🇪', Italy: '🇮🇹', Colombia: '🇨🇴', Uruguay: '🇺🇾',
  Morocco: '🇲🇦', Croatia: '🇭🇷', Senegal: '🇸🇳',
  'United States': '🇺🇸', USA: '🇺🇸', Mexico: '🇲🇽', Japan: '🇯🇵',
  Ecuador: '🇪🇨', 'South Korea': '🇰🇷', Canada: '🇨🇦', Australia: '🇦🇺',
  Switzerland: '🇨🇭', Poland: '🇵🇱', Denmark: '🇩🇰', Serbia: '🇷🇸',
  Turkey: '🇹🇷', Austria: '🇦🇹', Ukraine: '🇺🇦', Hungary: '🇭🇺',
  Slovakia: '🇸🇰', Romania: '🇷🇴', Slovenia: '🇸🇮', Czechia: '🇨🇿',
  Scotland: '🏴󠁧󠁢󠁳󠁣󠁴󠁿', Greece: '🇬🇷', Albania: '🇦🇱', Georgia: '🇬🇪',
  'Costa Rica': '🇨🇷', Panama: '🇵🇦', Venezuela: '🇻🇪', Chile: '🇨🇱',
  Paraguay: '🇵🇾', Bolivia: '🇧🇴', Honduras: '🇭🇳', 'El Salvador': '🇸🇻',
  'New Zealand': '🇳🇿', 'Saudi Arabia': '🇸🇦',
  Egypt: '🇪🇬', Iran: '🇮🇷', 'Cape Verde': '🇨🇻', 'Cape Verde Islands': '🇨🇻',
  'Bosnia & Herzegovina': '🇧🇦', 'Bosnia-Herzegovina': '🇧🇦',
  Peru: '🇵🇪', Sweden: '🇸🇪', Wales: '🏴󠁧󠁢󠁷󠁬󠁳󠁿', 'Northern Ireland': '🏴󠁧󠁢󠁮󠁩󠁲󠁿',
  'Republic of Ireland': '🇮🇪', Ireland: '🇮🇪', Iceland: '🇮🇸', Norway: '🇳🇴',
  Finland: '🇫🇮', 'Ivory Coast': '🇨🇮', "Cote d'Ivoire": '🇨🇮', Nigeria: '🇳🇬',
  Cameroon: '🇨🇲', Ghana: '🇬🇭', Algeria: '🇩🇿', Tunisia: '🇹🇳', Mali: '🇲🇱',
  'South Africa': '🇿🇦', Qatar: '🇶🇦', UAE: '🇦🇪', Iraq: '🇮🇶', Syria: '🇸🇾',
  China: '🇨🇳', 'China PR': '🇨🇳', India: '🇮🇳', Vietnam: '🇻🇳', Thailand: '🇹🇭',
  Jamaica: '🇯🇲', 'Trinidad and Tobago': '🇹🇹',
  Uzbekistan: '🇺🇿', 'DR Congo': '🇨🇩', 'Czech Republic': '🇨🇿',
  Curaçao: '🇨🇼', Haiti: '🇭🇹', Jordan: '🇯🇴',
};

export const COUNTRY_NAMES_ES: Record<string, string> = {
  Spain: 'España', England: 'Inglaterra', France: 'Francia', Germany: 'Alemania',
  Italy: 'Italia', Belgium: 'Bélgica', Netherlands: 'Países Bajos',
  Switzerland: 'Suiza', Poland: 'Polonia', Denmark: 'Dinamarca',
  Serbia: 'Serbia', Turkey: 'Turquía', Austria: 'Austria', Ukraine: 'Ucrania',
  Hungary: 'Hungría', Slovakia: 'Eslovaquia', Romania: 'Rumanía', Slovenia: 'Eslovenia',
  Czechia: 'República Checa', Scotland: 'Escocia', Greece: 'Grecia', Albania: 'Albania',
  Georgia: 'Georgia', Brazil: 'Brasil', Argentina: 'Argentina', Colombia: 'Colombia', Uruguay: 'Uruguay',
  Ecuador: 'Ecuador', Chile: 'Chile', Venezuela: 'Venezuela', Bolivia: 'Bolivia',
  Paraguay: 'Paraguay', 'United States': 'Estados Unidos', USA: 'EE.UU.', Mexico: 'México',
  Canada: 'Canadá', 'Costa Rica': 'Costa Rica', Panama: 'Panamá',
  Honduras: 'Honduras', 'El Salvador': 'El Salvador', Morocco: 'Marruecos', Senegal: 'Senegal', Egypt: 'Egipto',
  Japan: 'Japón', 'South Korea': 'Corea del Sur', 'Saudi Arabia': 'Arabia Saudita',
  Iran: 'Irán', Australia: 'Australia', 'New Zealand': 'Nueva Zelanda',
  'Cape Verde': 'Cabo Verde', 'Cape Verde Islands': 'Cabo Verde',
  'Bosnia & Herzegovina': 'Bosnia y Herzegovina', 'Bosnia-Herzegovina': 'Bosnia y Herzegovina',
  Croatia: 'Croacia', Peru: 'Perú', Sweden: 'Suecia', Wales: 'Gales', 'Northern Ireland': 'Irlanda del Norte',
  'Republic of Ireland': 'República de Irlanda', Ireland: 'Irlanda', Iceland: 'Islandia', Norway: 'Noruega',
  Finland: 'Finlandia', 'Ivory Coast': 'Costa de Marfil', "Cote d'Ivoire": 'Costa de Marfil', Nigeria: 'Nigeria',
  Cameroon: 'Camerún', Ghana: 'Ghana', Algeria: 'Argelia', Tunisia: 'Túnez', Mali: 'Malí',
  'South Africa': 'Sudáfrica', Qatar: 'Catar', UAE: 'EAU', Iraq: 'Irak', Syria: 'Siria',
  China: 'China', 'China PR': 'China', India: 'India', Vietnam: 'Vietnam', Thailand: 'Tailandia',
  Jamaica: 'Jamaica', 'Trinidad and Tobago': 'Trinidad y Tobago',
  Uzbekistan: 'Uzbekistán', 'DR Congo': 'RD Congo', 'Czech Republic': 'República Checa',
  Curaçao: 'Curazao', Haiti: 'Haití', Jordan: 'Jordania',
};

export function getFlag(teamName: string): string {
  return COUNTRY_FLAGS[teamName] || '🏳';
}

export function getEsName(teamName: string): string {
  const upper = teamName.toUpperCase();
  const found = Object.keys(COUNTRY_NAMES_ES).find(k => k.toUpperCase() === upper);
  return found ? COUNTRY_NAMES_ES[found] : teamName;
}

export function translateText(text: string): string {
  if (!text) return text;
  let translated = text;
  Object.keys(COUNTRY_NAMES_ES).forEach(enName => {
    // Replace whole words, ignoring case is optional but exact match is safer
    const regex = new RegExp(`\\b${enName}\\b`, 'g');
    translated = translated.replace(regex, COUNTRY_NAMES_ES[enName]);
  });
  return translated;
}
