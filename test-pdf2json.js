const fs = require('fs');
const PDFParser = require('pdf2json');

const pdfParser = new PDFParser();

pdfParser.on("pdfParser_dataError", errData => console.error(errData.parserError));
pdfParser.on("pdfParser_dataReady", pdfData => {
    fs.writeFileSync("pdf2json_output.json", JSON.stringify(pdfData, null, 2));
    console.log("Saved to pdf2json_output.json");
});

pdfParser.loadPDF("C:/Users/Aman/Downloads/1-2.pdf");
