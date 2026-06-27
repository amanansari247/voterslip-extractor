'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { getEnglishName } from '../lib/transliterate';

export default function Home() {
  return (
    <Suspense fallback={<div style={{color:'#fff',textAlign:'center',padding:'4rem'}}>Loading...</div>}>
      <VoterSlipApp />
    </Suspense>
  );
}

function VoterSlipApp() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [customBooth, setCustomBooth] = useState('');
  const [error, setError] = useState('');

  const searchParams = useSearchParams();
  const localFile = searchParams.get('localFile');

  useEffect(() => {
    if (localFile && !data && !loading) {
      handleTestFetch(localFile);
    }
  }, [localFile]);

  const handleTestFetch = async (filePath) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/extract?localFile=${encodeURIComponent(filePath)}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to extract data');
      const result = await response.json();
      if (result.error) throw new Error(result.error);
      setData(result);
      setCustomBooth(result.pollingStation || '');
    } catch (err) {
      setError(err.message);
      console.error("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/extract', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to extract data');
      const result = await response.json();
      if (result.error) throw new Error(result.error);

      setData(result);
      setCustomBooth(result.pollingStation || '');
    } catch (err) {
      setError(err.message);
      console.error("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleReset = () => {
    setData(null);
    setError('');
    setCustomBooth('');
  };

  // ---- RENDER ----
  return (
    <div className="app-container">

      {/* ===== HEADER ===== */}
      <header className="app-header no-print">
        <div className="logo-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14,2 14,8 20,8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10,9 9,9 8,9" />
          </svg>
        </div>
        <h1>Voter Slip Generator</h1>
        <p>Upload voter list PDFs and generate print-ready slips with photos</p>
      </header>

      {/* ===== UPLOAD ===== */}
      {!data && !loading && (
        <div className="no-print">
          <div className="upload-zone">
            <input type="file" accept=".pdf" onChange={handleFileUpload} />
            <div className="icon-wrap">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16,16 12,12 8,16" />
                <line x1="12" y1="12" x2="12" y2="21" />
                <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
              </svg>
            </div>
            <h3>Upload Voter List PDF</h3>
            <p className="subtext">Drag & drop or click to browse your file</p>
          </div>

          {error && (
            <div style={{textAlign:'center',color:'#ef4444',marginTop:'1rem',fontSize:'0.9rem'}}>{error}</div>
          )}
        </div>
      )}

      {/* ===== LOADING ===== */}
      {loading && (
        <div className="loading-state no-print">
          <div className="spinner"></div>
          <h2>Processing PDF...</h2>
          <p>Extracting voter data, photos, and layout information</p>
        </div>
      )}

      {/* ===== RESULTS ===== */}
      {data && (
        <div style={{animation: 'fadeIn 0.4s ease'}}>

          {/* Controls */}
          <div className="controls-bar no-print">
            <div className="input-group">
              <label>Polling Station / ਪੋਲਿੰਗ ਸਟੇਸ਼ਨ</label>
              <input
                type="text"
                value={customBooth}
                onChange={(e) => setCustomBooth(e.target.value)}
                placeholder="Enter polling station name..."
              />
            </div>

            <div className="btn-group">
              <button className="btn btn-secondary" onClick={handleReset}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1,4 1,10 7,10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                New Upload
              </button>
              <button className="btn btn-primary" onClick={handlePrint}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6,9 6,2 18,2 18,9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                Print / Download
              </button>
            </div>
          </div>

          {/* Stats */}
          <div className="stats-bar no-print">
            <div className="stat-item">
              <span className="stat-label">Total Voters:</span>
              <span className="stat-value">{data.voters?.length || 0}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Photos Found:</span>
              <span className="stat-value">{data.voters?.filter(v => v.photo).length || 0}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Pages (Print):</span>
              <span className="stat-value">{Math.ceil((data.voters?.length || 0) / 12)}</span>
            </div>
          </div>

          {/* ===== PRINTABLE SLIPS ===== */}
          <div className="slip-grid" id="printable-area">
            {data.voters?.map((voter, idx) => (
              <div key={idx} className="slip-item">
                <div className="slip-inner">

                  {/* LEFT SIDE: Text Details */}
                  <div className="slip-left">
                    <div className="slip-header-row">
                      <div className="slip-srno">{voter.serial}</div>
                      <div className="slip-booth-no">ਬੂਥ ਨੰ.: 1 / 1</div>
                    </div>

                    <div className="detail-row">
                      <span className="label">ਨਾਮ:-</span>
                      <span className="value">{voter.name}</span>
                    </div>

                    <div className="english-name-row">
                      {getEnglishName(voter.name)}
                    </div>

                    <div className="detail-row">
                      <span className="label">ਪਤੀ :-</span>
                      <span className="value">{voter.relativeName}</span>
                    </div>

                    <div className="detail-row">
                      <span className="label">ਮਕਾਨ ਨੰ.:-</span>
                      <span className="value">{voter.houseNumber}</span>
                    </div>

                    <div className="detail-row polling-row">
                      <span className="label">ਪੋਲਿੰਗ:-</span>
                      <span className="value">{customBooth}</span>
                    </div>
                  </div>

                  {/* RIGHT SIDE: Photo + Gender/Age */}
                  <div className="slip-right">
                    <div className="photo-box">
                      {voter.photo ? (
                        <img src={voter.photo} alt="Voter" />
                      ) : (
                        <span className="no-photo">No<br/>Photo</span>
                      )}
                    </div>
                    <div className="photo-details">
                      {voter.gender === 'ਇਸਤਰਤ' || voter.gender === 'ਔਰਤ' ? 'Female' : 'Male'}&nbsp;&nbsp;{voter.age}
                    </div>
                  </div>

                </div>
              </div>
            ))}
          </div>

        </div>
      )}
    </div>
  );
}
