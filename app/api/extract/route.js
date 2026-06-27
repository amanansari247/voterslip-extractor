import { NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export async function POST(request) {
  try {
    const localFile = request.nextUrl.searchParams.get('localFile');
    const tempDir = path.join(process.cwd(), 'tmp');
    await mkdir(tempDir, { recursive: true });
    
    let filepath = '';
    const outpath = path.join(tempDir, `out-${Date.now()}.json`);

    if (localFile) {
      filepath = localFile; // Use local file directly for testing
    } else {
      const formData = await request.formData();
      const file = formData.get('file');

      if (!file) {
        return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
      }

      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);

      const filename = `upload-${Date.now()}.pdf`;
      filepath = path.join(tempDir, filename);

      await writeFile(filepath, buffer);
    }

    // Run python script
    const pythonScript = path.join(process.cwd(), 'lib', 'python_scripts', 'extractor.py');
    const { stdout, stderr } = await execAsync(`python "${pythonScript}" "${filepath}" "${outpath}"`);

    if (stderr) {
      console.warn('Python stderr:', stderr);
    }

    // Read the generated JSON file
    const fs = require('fs');
    const data = JSON.parse(fs.readFileSync(outpath, 'utf-8'));

    // Cleanup
    try {
      fs.unlinkSync(filepath);
      fs.unlinkSync(outpath);
    } catch (e) {
      console.error('Cleanup error:', e);
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Extraction error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
