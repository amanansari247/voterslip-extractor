const fs = require('fs');
const pdf = require('pdf-parse');

console.log(pdf);
let dataBuffer = fs.readFileSync('C:/Users/Aman/Downloads/1-2.pdf');

pdf(dataBuffer).then(function(data) {
    fs.writeFileSync('pdf-parse-output.txt', data.text);
    console.log('Saved to pdf-parse-output.txt');
}).catch(console.error);
