import { NextResponse } from 'next/server';
import { mkdir, readFile, unlink, writeFile } from 'fs/promises';
import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execFileAsync = promisify(execFile);

export const dynamic = 'force-dynamic';

export async function POST(request) {
  const tempDir = path.join(process.cwd(), 'tmp');
  let uploadedFilepath = '';
  let outpath = '';

  try {
    await mkdir(tempDir, { recursive: true });

    const localFile = request.nextUrl.searchParams.get('localFile');
    outpath = path.join(tempDir, `out-${Date.now()}.json`);
    let filepath = localFile || '';

    if (!filepath) {
      const formData = await request.formData();
      const file = formData.get('file');

      if (!file) {
        return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
      }

      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);
      uploadedFilepath = path.join(tempDir, `upload-${Date.now()}.pdf`);
      filepath = uploadedFilepath;

      await writeFile(uploadedFilepath, buffer);
    }

    const pythonScript = path.join(process.cwd(), 'lib', 'python_scripts', 'extractor.py');

    await execFileAsync('python', [pythonScript, filepath, outpath], {
      maxBuffer: 1024 * 1024 * 20,
    });

    const payload = await readFile(outpath, 'utf-8');
    return NextResponse.json(JSON.parse(payload));
  } catch (error) {
    console.error('Extraction error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await Promise.allSettled([
      uploadedFilepath ? unlink(uploadedFilepath) : Promise.resolve(),
      outpath ? unlink(outpath) : Promise.resolve(),
    ]);
  }
}
