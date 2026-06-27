// Gurmukhi to Latin transliteration
// Simplified for Punjabi names

const VOWEL_SIGNS = {
  '\u0A3E': 'a',   // ਾ
  '\u0A3F': 'i',   // ਿ
  '\u0A40': 'ee',  // ੀ
  '\u0A41': 'u',   // ੁ
  '\u0A42': 'oo',  // ੂ
  '\u0A47': 'e',   // ੇ
  '\u0A48': 'ai',  // ੈ
  '\u0A4B': 'o',   // ੋ
  '\u0A4C': 'au',  // ੌ
};

const CONSONANTS = {
  '\u0A15': 'k', '\u0A16': 'kh', '\u0A17': 'g', '\u0A18': 'gh', '\u0A19': 'ng',
  '\u0A1A': 'ch', '\u0A1B': 'chh', '\u0A1C': 'j', '\u0A1D': 'jh', '\u0A1E': 'ny',
  '\u0A1F': 't', '\u0A20': 'th', '\u0A21': 'd', '\u0A22': 'dh', '\u0A23': 'n',
  '\u0A24': 't', '\u0A25': 'th', '\u0A26': 'd', '\u0A27': 'dh', '\u0A28': 'n',
  '\u0A2A': 'p', '\u0A2B': 'ph', '\u0A2C': 'b', '\u0A2D': 'bh', '\u0A2E': 'm',
  '\u0A2F': 'y', '\u0A30': 'r', '\u0A32': 'l', '\u0A33': 'l', '\u0A35': 'v',
  '\u0A38': 's', '\u0A39': 'h', '\u0A5C': 'r',
};

const INDEPENDENT_VOWELS = {
  '\u0A05': 'a', '\u0A06': 'a', '\u0A07': 'i', '\u0A08': 'ee',
  '\u0A09': 'u', '\u0A0A': 'oo', '\u0A0F': 'e', '\u0A10': 'ai',
  '\u0A13': 'o', '\u0A14': 'au',
};

const NUKTA = {
  '\u0A59': 'kh', '\u0A5A': 'gh', '\u0A5B': 'z', '\u0A5E': 'f',
};

function transliterateWord(word) {
  if (!word) return '';
  let result = '';
  const len = word.length;
  
  for (let i = 0; i < len; i++) {
    const ch = word[i];
    if (ch === '\u0A3C' || ch === '\u0A4D' || ch === '\u0A71' || ch === '\u0A73' || ch === '\u0A72') continue;
    if (ch === '\u0A70' || ch === '\u0A02') { result += 'n'; continue; }
    
    if (INDEPENDENT_VOWELS[ch]) { result += INDEPENDENT_VOWELS[ch]; continue; }
    if (VOWEL_SIGNS[ch]) { result += VOWEL_SIGNS[ch]; continue; }
    
    let cons = NUKTA[ch] || CONSONANTS[ch];
    if (cons) {
      result += cons;
      // Add implicit 'a' only after the first character of the word, if no vowel follows
      if (i === 0) {
        let hasVowelNext = false;
        if (i + 1 < len) {
          const next = word[i+1];
          if (VOWEL_SIGNS[next] || next === '\u0A4D' || next === '\u0A71') hasVowelNext = true;
        }
        if (!hasVowelNext) result += 'a';
      }
      // Add implicit 'a' for 'm' or 'l' if surrounded by consonants (e.g. Amarjit -> m needs a)
      else if (i > 0 && i < len - 1 && (ch === '\u0A2E' || ch === '\u0A32' || ch === '\u0A2C')) {
         let hasVowelNext = false;
         if (i + 1 < len) {
           const next = word[i+1];
           if (VOWEL_SIGNS[next] || next === '\u0A4D' || next === '\u0A71') hasVowelNext = true;
         }
         if (!hasVowelNext) result += 'a';
      }
      continue;
    }
    result += ch;
  }
  
  // Cleanups for common Punjabi names
  result = result.replace(/ee/g, 'ee');
  result = result.replace(/pareet/gi, 'preet');
  result = result.replace(/jeet/gi, 'jeet');
  result = result.replace(/vindr/gi, 'vinder');
  result = result.replace(/vindar/gi, 'vinder');
  result = result.replace(/singh/gi, 'Singh');
  result = result.replace(/kaur/gi, 'Kaur');
  result = result.replace(/sharm/gi, 'Sharma');
  
  return result;
}

export function transliterateGurmukhi(text) {
  if (!text) return '';
  return text
    .split(/\s+/)
    .filter(w => w.length > 0)
    .map(word => {
      const roman = transliterateWord(word);
      if (roman.length === 0) return '';
      return roman.charAt(0).toUpperCase() + roman.slice(1).toLowerCase();
    })
    .join(' ')
    .replace(/Singh/ig, 'Singh')
    .replace(/Kaur/ig, 'Kaur')
    .trim();
}

export function getEnglishName(name) {
  return transliterateGurmukhi(name);
}
