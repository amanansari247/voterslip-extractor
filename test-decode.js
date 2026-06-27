const fs = require('fs');
const PDFParser = require('pdf2json');

const pdfParser = new PDFParser();

pdfParser.on("pdfParser_dataError", errData => console.error(errData.parserError));
pdfParser.on("pdfParser_dataReady", pdfData => {
    const page2 = pdfData.Pages[1];
    
    // Decode all texts and attach coordinates
    let texts = page2.Texts.map(t => ({
        text: decodeURIComponent(t.R[0].T),
        x: t.x,
        y: t.y
    }));
    
    console.log("Decoded Texts (first 30):");
    console.log(texts.slice(0, 30));
});

pdfParser.loadPDF("C:/Users/Aman/Downloads/1-2.pdf");
