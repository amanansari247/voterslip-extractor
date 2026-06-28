'use client';

/* eslint-disable @next/next/no-img-element */

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  Check,
  Copy,
  Grid3x3,
  Loader2,
  Maximize2,
  Plus,
  Printer,
  RotateCcw,
  Scissors,
  Trash2,
  Upload,
  Wand2,
} from 'lucide-react';

const MIN_BOX_SIZE = 24;
const MAX_GRID_LINE_GAP = 12;

const DEFAULT_GRID = {
  cols: 3,
  rows: 10,
  gapX: 0,
  gapY: 0,
  cardWidth: 480,
  cardHeight: 200,
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min));
}

function sortBoxes(a, b) {
  return a.pageIndex - b.pageIndex || a.y - b.y || a.x - b.x;
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

function normalizeBox(box, page) {
  const width = clamp(box.width, MIN_BOX_SIZE, page.width);
  const height = clamp(box.height, MIN_BOX_SIZE, page.height);
  const x = clamp(box.x, 0, Math.max(0, page.width - width));
  const y = clamp(box.y, 0, Math.max(0, page.height - height));
  return { ...box, x, y, width: Math.min(width, page.width - x), height: Math.min(height, page.height - y) };
}

function createTableRegion(page) {
  return normalizeBox({
    id: `p${page.index}-region-${Date.now()}`,
    pageIndex: page.index,
    x: page.width * 0.06,
    y: page.height * 0.16,
    width: page.width * 0.88,
    height: page.height * 0.78,
    source: 'table-region',
  }, page);
}

function getManualGridDefaults(defaults = {}) {
  return {
    ...DEFAULT_GRID,
    cols: clamp(Number(defaults.cols) || DEFAULT_GRID.cols, 1, 8),
    rows: DEFAULT_GRID.rows,
  };
}

function isTableRegion(box) {
  return String(box.source || '').startsWith('table-region');
}

function findProjectionLines(counts, threshold, clusterGap = 5) {
  const clusters = [];

  counts.forEach((value, index) => {
    if (value < threshold) return;
    const last = clusters[clusters.length - 1];
    if (!last || index - last[last.length - 1].index > clusterGap) {
      clusters.push([{ index, value }]);
    } else {
      last.push({ index, value });
    }
  });

  return clusters.map((cluster) => {
    const strongest = cluster.reduce((best, item) => (item.value > best.value ? item : best), cluster[0]);
    return {
      position: (cluster[0].index + cluster[cluster.length - 1].index) / 2,
      strength: strongest.value,
    };
  });
}

function buildEvenGridLines(maxValue, parts) {
  return Array.from({ length: parts + 1 }, (_, index) => (maxValue * index) / parts);
}

function pickDetectedGridLines(lines, maxValue, parts) {
  if (lines.length < parts + 1) return null;

  const sorted = [...lines].sort((a, b) => a.position - b.position);
  let best = null;

  for (let startIndex = 0; startIndex < sorted.length - 1; startIndex += 1) {
    for (let endIndex = startIndex + 1; endIndex < sorted.length; endIndex += 1) {
      const start = sorted[startIndex];
      const end = sorted[endIndex];
      const span = end.position - start.position;
      const expectedGap = span / parts;
      if (expectedGap < MIN_BOX_SIZE * 1.4) continue;

      const tolerance = Math.max(8, expectedGap * 0.22);
      const used = new Set([startIndex, endIndex]);
      const sequence = [start.position];
      let missing = 0;
      let distancePenalty = 0;
      let strength = start.strength + end.strength;

      for (let index = 1; index < parts; index += 1) {
        const expected = start.position + expectedGap * index;
        let matchIndex = -1;
        let matchScore = Number.POSITIVE_INFINITY;

        sorted.forEach((line, lineIndex) => {
          if (used.has(lineIndex)) return;
          const distance = Math.abs(line.position - expected);
          if (distance > tolerance) return;

          const score = distance - line.strength * 0.002;
          if (score < matchScore) {
            matchScore = score;
            matchIndex = lineIndex;
          }
        });

        if (matchIndex >= 0) {
          const match = sorted[matchIndex];
          used.add(matchIndex);
          sequence.push(match.position);
          distancePenalty += Math.abs(match.position - expected);
          strength += match.strength;
        } else {
          missing += 1;
          sequence.push(expected);
          distancePenalty += tolerance;
        }
      }

      if (missing > Math.max(1, Math.floor(parts * 0.2))) continue;

      sequence.push(end.position);
      const gaps = sequence.slice(1).map((line, index) => line - sequence[index]);
      if (gaps.some((gap) => gap < MIN_BOX_SIZE)) continue;

      const averageGap = gaps.reduce((sum, gap) => sum + gap, 0) / gaps.length;
      const variance = gaps.reduce((sum, gap) => sum + (gap - averageGap) ** 2, 0) / gaps.length;
      const score = strength + span * 0.5 - distancePenalty * 12 - variance * 0.04 - missing * 500;

      if (!best || score > best.score) {
        best = { score, sequence };
      }
    }
  }

  return best?.sequence || null;
}

function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[middle - 1] + sorted[middle]) / 2
    : sorted[middle];
}

function getTypicalGridGap(lines, minGap, maxGap) {
  const positions = [...lines].map((line) => line.position).sort((a, b) => a - b);
  const gaps = [];

  for (let index = 0; index < positions.length - 1; index += 1) {
    const gap = positions[index + 1] - positions[index];
    if (gap >= minGap && gap <= maxGap) gaps.push(gap);
  }

  return median(gaps);
}

function pickRegularGridLines(lines, maxValue, expectedParts, minGap, maxGap) {
  const positions = [...lines].map((line) => line.position).sort((a, b) => a - b);
  const typicalGap = getTypicalGridGap(lines, minGap, maxGap);
  if (!typicalGap) return null;

  const tolerance = Math.max(12, typicalGap * 0.22);
  let best = null;

  positions.forEach((start) => {
    const sequence = [start];
    let current = start;

    while (sequence.length <= expectedParts + 1) {
      const expected = current + typicalGap;
      const next = positions
        .filter((position) => position > current + minGap * 0.5 && Math.abs(position - expected) <= tolerance)
        .sort((a, b) => Math.abs(a - expected) - Math.abs(b - expected))[0];

      if (!next) break;
      sequence.push(next);
      current = next;
    }

    if (sequence.length < 2) return;

    const bottomExpected = sequence[sequence.length - 1] + typicalGap;
    const bottomInside = bottomExpected <= maxValue + tolerance;
    const completed = bottomInside && sequence.length <= expectedParts
      ? [...sequence, Math.min(bottomExpected, maxValue)]
      : sequence;
    const parts = completed.length - 1;
    if (parts < 1) return;

    const gaps = completed.slice(1).map((line, index) => line - completed[index]);
    if (gaps.some((gap) => gap < minGap * 0.65 || gap > maxGap * 1.35)) return;

    const averageGap = gaps.reduce((sum, gap) => sum + gap, 0) / gaps.length;
    const variance = gaps.reduce((sum, gap) => sum + (gap - averageGap) ** 2, 0) / gaps.length;
    const score = parts * 1000 - variance - Math.abs(expectedParts - parts) * 45;

    if (!best || score > best.score) {
      best = { score, lines: completed };
    }
  });

  return best?.lines || null;
}

function fallbackGridInsideRegion(region, page, settings) {
  const cols = clamp(Number(settings.cols) || 3, 1, 8);
  const rows = clamp(Number(settings.rows) || 10, 1, 30);
  const cellWidth = region.width / cols;
  const cellHeight = region.height / rows;
  const generated = [];

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      generated.push(normalizeBox({
        id: `p${page.index}-cell-${row}-${col}-${Date.now()}`,
        pageIndex: page.index,
        x: region.x + col * cellWidth,
        y: region.y + row * cellHeight,
        width: cellWidth,
        height: cellHeight,
        source: 'region-divide',
      }, page));
    }
  }

  return generated;
}

async function detectGridInsideRegion(page, region, settings) {
  const cols = clamp(Number(settings.cols) || 3, 1, 8);
  const rows = clamp(Number(settings.rows) || 10, 1, 30);
  const sourceImage = await loadImage(page.image);
  const canvas = document.createElement('canvas');
  canvas.width = page.width;
  canvas.height = page.height;
  const context = canvas.getContext('2d');
  context.drawImage(sourceImage, 0, 0, page.width, page.height);

  const x = Math.max(0, Math.round(region.x));
  const y = Math.max(0, Math.round(region.y));
  const width = Math.max(MIN_BOX_SIZE, Math.min(Math.round(region.width), page.width - x));
  const height = Math.max(MIN_BOX_SIZE, Math.min(Math.round(region.height), page.height - y));
  const imageData = context.getImageData(x, y, width, height).data;
  const rowRuns = new Array(height).fill(0);
  const colRuns = new Array(width).fill(0);
  const activeColStarts = new Array(width).fill(-1);
  const activeColLasts = new Array(width).fill(-1);
  const activeColGaps = new Array(width).fill(0);

  for (let row = 0; row < height; row += 1) {
    let activeRowStart = -1;
    let activeRowLast = -1;
    let activeRowGap = 0;
    let longestRowRun = 0;

    for (let col = 0; col < width; col += 1) {
      const offset = (row * width + col) * 4;
      const brightness = (imageData[offset] + imageData[offset + 1] + imageData[offset + 2]) / 3;
      if (brightness < 190) {
        if (activeRowStart < 0) activeRowStart = col;
        activeRowLast = col;
        activeRowGap = 0;
        longestRowRun = Math.max(longestRowRun, activeRowLast - activeRowStart + 1);

        if (activeColStarts[col] < 0) activeColStarts[col] = row;
        activeColLasts[col] = row;
        activeColGaps[col] = 0;
        colRuns[col] = Math.max(colRuns[col], activeColLasts[col] - activeColStarts[col] + 1);
      } else {
        if (activeRowStart >= 0) {
          activeRowGap += 1;
          if (activeRowGap > MAX_GRID_LINE_GAP) {
            activeRowStart = -1;
            activeRowLast = -1;
            activeRowGap = 0;
          }
        }

        if (activeColStarts[col] >= 0) {
          activeColGaps[col] += 1;
          if (activeColGaps[col] > MAX_GRID_LINE_GAP) {
            activeColStarts[col] = -1;
            activeColLasts[col] = -1;
            activeColGaps[col] = 0;
          }
        }
      }
    }

    rowRuns[row] = longestRowRun;
  }

  const pageHeight = Math.round(page.height);
  const rowCandidates = findProjectionLines(rowRuns, width * 0.35, 3);
  const columnCandidates = findProjectionLines(colRuns, height * 0.35, 3);
  const detectedRows = pickRegularGridLines(
    rowCandidates,
    height,
    rows,
    pageHeight * 0.045,
    pageHeight * 0.12,
  );
  const detectedColumns = pickDetectedGridLines(columnCandidates, width, cols);
  const evenRowHeight = height / rows;

  if (!detectedRows && evenRowHeight < pageHeight * 0.06) {
    throw new Error('The selected table area is too short for 10 rows. Drag the bottom of the table box down to include the full table, or reduce rows.');
  }

  const rowLines = detectedRows || buildEvenGridLines(height, rows);
  const columnLines = detectedColumns || buildEvenGridLines(width, cols);
  const source = detectedRows ? 'region-detected' : 'region-divide';

  const generated = [];
  for (let row = 0; row < rowLines.length - 1; row += 1) {
    for (let col = 0; col < columnLines.length - 1; col += 1) {
      const top = rowLines[row];
      const bottom = rowLines[row + 1];
      const left = columnLines[col];
      const right = columnLines[col + 1];
      if (bottom - top < MIN_BOX_SIZE || right - left < MIN_BOX_SIZE) continue;

      generated.push(normalizeBox({
        id: `p${page.index}-detected-${row}-${col}-${Date.now()}`,
        pageIndex: page.index,
        x: x + left,
        y: y + top,
        width: right - left,
        height: bottom - top,
        source,
      }, page));
    }
  }

  return generated.length ? generated : fallbackGridInsideRegion(region, page, settings);
}

export default function Home() {
  return (
    <Suspense fallback={<div className="app-loading">Loading...</div>}>
      <VoterSlipApp />
    </Suspense>
  );
}

function VoterSlipApp() {
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [data, setData] = useState(null);
  const [mode, setMode] = useState('region');
  const [boxes, setBoxes] = useState([]);
  const [preparedCards, setPreparedCards] = useState([]);
  const [customBooth, setCustomBooth] = useState('');
  const [error, setError] = useState('');
  const [activePageIndex, setActivePageIndex] = useState(0);
  const [selectedBoxId, setSelectedBoxId] = useState('');
  const [gridSettings, setGridSettings] = useState(DEFAULT_GRID);
  const [dragState, setDragState] = useState(null);

  const searchParams = useSearchParams();
  const localFile = searchParams.get('localFile');

  const pageByIndex = useMemo(() => {
    const map = new Map();
    data?.pages?.forEach((page) => map.set(page.index, page));
    return map;
  }, [data]);

  const activePage = data?.pages?.[activePageIndex] || null;
  const activePageBoxes = useMemo(() => {
    if (!activePage) return [];
    return boxes.filter((box) => box.pageIndex === activePage.index).sort(sortBoxes);
  }, [activePage, boxes]);

  const activePageRegion = useMemo(
    () => activePageBoxes.find(isTableRegion) || null,
    [activePageBoxes],
  );

  const selectedBox = useMemo(
    () => boxes.find((box) => box.id === selectedBoxId) || null,
    [boxes, selectedBoxId],
  );

  const isRegionMode = mode === 'region';
  const hasDetectedCuts = useMemo(() => boxes.some((box) => !isTableRegion(box)), [boxes]);
  const detectedCutCount = useMemo(() => boxes.filter((box) => !isTableRegion(box)).length, [boxes]);
  const tableRegionCount = boxes.length - detectedCutCount;
  const selectedBoxIsRegion = selectedBox ? isTableRegion(selectedBox) : Boolean(activePageRegion);

  const applyExtractionResult = useCallback((result) => {
    const firstPagePosition = Math.max(
      0,
      (result.pages || []).findIndex((page) => page.index === (result.cardStartPage || 0)),
    );

    setData(result);
    setMode('region');
    setBoxes([]);
    setPreparedCards([]);
    setCustomBooth(result.pollingStation || '');
    setGridSettings(getManualGridDefaults(result.gridDefaults));
    setActivePageIndex(firstPagePosition);
    setSelectedBoxId('');
  }, []);

  const extractFromLocalPath = useCallback(async (filePath) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/extract?localFile=${encodeURIComponent(filePath)}`, {
        method: 'POST',
      });
      const result = await response.json();
      if (!response.ok || result.error) {
        throw new Error(result.error || 'Failed to extract PDF');
      }
      applyExtractionResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [applyExtractionResult]);

  useEffect(() => {
    if (!localFile || data || loading) return undefined;

    const timer = window.setTimeout(() => {
      extractFromLocalPath(localFile);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [data, extractFromLocalPath, loading, localFile]);

  useEffect(() => {
    if (!dragState) return undefined;

    function handlePointerMove(event) {
      event.preventDefault();
      const page = pageByIndex.get(dragState.startBox.pageIndex);
      if (!page) return;

      const deltaX = (event.clientX - dragState.pointerX) * (page.width / dragState.displayWidth);
      const deltaY = (event.clientY - dragState.pointerY) * (page.height / dragState.displayHeight);
      const mode = dragState.mode;
      const start = dragState.startBox;
      const next = { ...start };

      if (mode === 'move') {
        next.x = start.x + deltaX;
        next.y = start.y + deltaY;
      } else {
        if (mode.includes('e')) {
          next.width = start.width + deltaX;
        }
        if (mode.includes('s')) {
          next.height = start.height + deltaY;
        }
        if (mode.includes('w')) {
          next.x = start.x + deltaX;
          next.width = start.width - deltaX;
        }
        if (mode.includes('n')) {
          next.y = start.y + deltaY;
          next.height = start.height - deltaY;
        }
      }

      if (next.width < MIN_BOX_SIZE) {
        if (mode.includes('w')) next.x = start.x + start.width - MIN_BOX_SIZE;
        next.width = MIN_BOX_SIZE;
      }
      if (next.height < MIN_BOX_SIZE) {
        if (mode.includes('n')) next.y = start.y + start.height - MIN_BOX_SIZE;
        next.height = MIN_BOX_SIZE;
      }

      setBoxes((current) =>
        current.map((box) => (box.id === dragState.startBox.id ? normalizeBox(next, page) : box)),
      );
    }

    function handlePointerUp() {
      setDragState(null);
    }

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [dragState, pageByIndex]);

  async function handleFileUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file.');
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
      const result = await response.json();
      if (!response.ok || result.error) {
        throw new Error(result.error || 'Failed to extract PDF');
      }
      applyExtractionResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      event.target.value = '';
    }
  }

  function resetApp() {
    setData(null);
    setMode('region');
    setBoxes([]);
    setPreparedCards([]);
    setCustomBooth('');
    setError('');
    setActivePageIndex(0);
    setSelectedBoxId('');
    setGridSettings(DEFAULT_GRID);
  }

  function startDrag(event, box, mode) {
    const pageNode = event.currentTarget.closest('.page-stage');
    if (!pageNode) return;
    const rect = pageNode.getBoundingClientRect();
    event.preventDefault();
    event.stopPropagation();
    setSelectedBoxId(box.id);
    setDragState({
      mode,
      pointerX: event.clientX,
      pointerY: event.clientY,
      displayWidth: rect.width,
      displayHeight: rect.height,
      startBox: box,
    });
  }

  function updateSelectedBox(field, value) {
    if (!selectedBox) return;
    const page = pageByIndex.get(selectedBox.pageIndex);
    if (!page) return;
    const numericValue = Number(value);
    setBoxes((current) =>
      current.map((box) =>
        box.id === selectedBox.id ? normalizeBox({ ...box, [field]: numericValue }, page) : box,
      ),
    );
  }

  function addBox() {
    if (!activePage) return;

    if (isRegionMode) {
      const existingRegion = activePageRegion;
      const region = existingRegion
        ? normalizeBox({ ...existingRegion, id: `p${activePage.index}-region-${Date.now()}` }, activePage)
        : createTableRegion(activePage);

      setBoxes((current) => [
        ...current.filter((box) => box.pageIndex !== activePage.index),
        region,
      ].sort(sortBoxes));
      setSelectedBoxId(region.id);
      return;
    }

    const base = selectedBox?.pageIndex === activePage.index
      ? selectedBox
      : activePageBoxes[0] || {
          x: activePage.width * 0.06,
          y: activePage.height * 0.09,
          width: gridSettings.cardWidth,
          height: gridSettings.cardHeight,
        };

    const id = `p${activePage.index}-manual-${Date.now()}`;
    const nextBox = normalizeBox({
      id,
      pageIndex: activePage.index,
      x: base.x + 18,
      y: base.y + 18,
      width: base.width,
      height: base.height,
      source: 'manual',
    }, activePage);

    setBoxes((current) => [...current, nextBox].sort(sortBoxes));
    setSelectedBoxId(id);
  }

  function deleteSelectedBox() {
    if (!selectedBoxId) return;
    setBoxes((current) => current.filter((box) => box.id !== selectedBoxId));
    setSelectedBoxId('');
  }

  function copySelectedSize(scope) {
    if (!selectedBox) return;
    setBoxes((current) =>
      current.map((box) => {
        if (scope === 'page' && box.pageIndex !== selectedBox.pageIndex) return box;
        const page = pageByIndex.get(box.pageIndex);
        if (!page) return box;
        return normalizeBox({ ...box, width: selectedBox.width, height: selectedBox.height }, page);
      }),
    );
  }

  function goToNextPage() {
    if (!data?.pages?.length) return;
    setActivePageIndex((current) => Math.min(current + 1, data.pages.length - 1));
    setSelectedBoxId('');
  }

  async function findGridInsideRegions() {
    if (!data || !activePage) {
      return;
    }

    if (!activePageRegion) {
      setError('Select the table area on this page first.');
      return;
    }

    const pageIndex = activePage.index;
    setPreparing(true);
    setError('');
    try {
      const generated = await detectGridInsideRegion(activePage, activePageRegion, gridSettings);

      if (generated.length === 0) {
        throw new Error('No grid was found inside the selected table area.');
      }

      setBoxes((current) => [
        ...current.filter((box) => box.pageIndex !== pageIndex),
        ...generated,
      ].sort(sortBoxes));
      setSelectedBoxId('');
      goToNextPage();
    } catch (err) {
      setError(err.message || 'Could not find the grid inside the selected table.');
    } finally {
      setPreparing(false);
    }
  }

  async function prepareSlips() {
    if (!data || boxes.length === 0) return;
    setPreparing(true);
    setError('');
    try {
      const imageCache = new Map();
      const cards = [];
      const orderedBoxes = boxes.filter((box) => !isTableRegion(box)).sort(sortBoxes);

      for (const box of orderedBoxes) {
        const page = pageByIndex.get(box.pageIndex);
        if (!page) continue;
        let sourceImage = imageCache.get(page.index);
        if (!sourceImage) {
          sourceImage = await loadImage(page.image);
          imageCache.set(page.index, sourceImage);
        }

        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(box.width));
        canvas.height = Math.max(1, Math.round(box.height));
        const context = canvas.getContext('2d');
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(
          sourceImage,
          box.x,
          box.y,
          box.width,
          box.height,
          0,
          0,
          canvas.width,
          canvas.height,
        );

        cards.push({
          image: canvas.toDataURL('image/jpeg', 0.92),
          pageNumber: page.pageNumber,
        });
      }

      setPreparedCards(cards);
    } catch (err) {
      setError(err.message || 'Could not prepare the selected slips.');
    } finally {
      setPreparing(false);
    }
  }

  function printSlips() {
    window.print();
  }

  const showPrepared = preparedCards.length > 0;

  return (
    <main className="app-shell">
      <header className="topbar no-print">
        <div>
          <p className="eyebrow">Voter PDF Extraction</p>
          <h1>Crop, Confirm, Print</h1>
        </div>
        {data && (
          <div className="topbar-actions">
            <button className="icon-btn" type="button" onClick={resetApp} title="New upload">
              <RotateCcw size={18} />
            </button>
            {showPrepared ? (
              <>
                <button className="btn btn-secondary" type="button" onClick={() => setPreparedCards([])}>
                  <ArrowLeft size={16} />
                  Edit Cuts
                </button>
                <button className="btn btn-primary" type="button" onClick={printSlips}>
                  <Printer size={16} />
                  Print
                </button>
              </>
            ) : (
              <button className="btn btn-primary" type="button" onClick={findGridInsideRegions} disabled={preparing || !activePageRegion}>
                {preparing ? <Loader2 className="spin-icon" size={16} /> : <Wand2 size={16} />}
                Find Grid This Page
              </button>
            )}
          </div>
        )}
      </header>

      {!data && !loading && (
        <section className="upload-panel no-print">
          <label className="upload-target">
            <input type="file" accept=".pdf" onChange={handleFileUpload} />
            <Upload size={34} />
            <span>Upload voter PDF</span>
          </label>
          {error && <p className="error-text">{error}</p>}
        </section>
      )}

      {loading && (
        <section className="loading-panel no-print">
          <Loader2 className="spin-icon" size={34} />
          <h2>Analyzing PDF</h2>
          <p>Preparing full-page previews and editable crop boxes.</p>
        </section>
      )}

      {data && !showPrepared && (
        <section className="workspace no-print">
          <aside className="side-panel">
            <div className="field-block">
              <label>Polling text</label>
              <input
                type="text"
                value={customBooth}
                onChange={(event) => setCustomBooth(event.target.value)}
                placeholder="Enter polling station"
              />
            </div>

            <div className="stats-strip">
              <span>{tableRegionCount} tables</span>
              <span>{detectedCutCount} cuts</span>
            </div>

            <div className="page-list">
              {data.pages.map((page, index) => {
                const pageBoxCount = boxes.filter((box) => box.pageIndex === page.index).length;
                return (
                  <button
                    key={page.index}
                    className={`page-thumb ${index === activePageIndex ? 'active' : ''}`}
                    type="button"
                    onClick={() => setActivePageIndex(index)}
                  >
                    <img src={page.image} alt={`Page ${page.pageNumber}`} />
                    <span>Page {page.pageNumber}</span>
                    <strong>{pageBoxCount}</strong>
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="editor-panel">
            <div className="editor-toolbar">
              <button className="btn btn-secondary" type="button" onClick={addBox}>
                <Plus size={16} />
                {isRegionMode ? 'Select Table' : 'Add Cut'}
              </button>
              <button className="btn btn-secondary danger" type="button" onClick={deleteSelectedBox} disabled={!selectedBox}>
                <Trash2 size={16} />
                Delete
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => copySelectedSize('page')} disabled={!selectedBox}>
                <Copy size={16} />
                Same Size Page
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => copySelectedSize('all')} disabled={!selectedBox}>
                <Maximize2 size={16} />
                Same Size All
              </button>
            </div>

            <div className="page-stage-shell">
              {activePage && (
                <div className="page-stage">
                  <img className="page-image" src={activePage.image} alt={`PDF page ${activePage.pageNumber}`} />
                  <div className="box-layer">
                    {activePageBoxes.map((box, index) => {
                      const boxIsRegion = isTableRegion(box);
                      const isSelected = box.id === selectedBoxId;
                      return (
                        <button
                          key={box.id}
                          className={`crop-box ${boxIsRegion ? 'region-box' : ''} ${isSelected ? 'selected' : ''}`}
                          style={{
                            left: `${(box.x / activePage.width) * 100}%`,
                            top: `${(box.y / activePage.height) * 100}%`,
                            width: `${(box.width / activePage.width) * 100}%`,
                            height: `${(box.height / activePage.height) * 100}%`,
                          }}
                          type="button"
                          onPointerDown={(event) => startDrag(event, box, 'move')}
                          onClick={() => setSelectedBoxId(box.id)}
                          title={`${boxIsRegion ? 'Table' : 'Cut'} ${index + 1}`}
                        >
                          <span className="crop-label">{boxIsRegion ? 'T' : index + 1}</span>
                          {isSelected && ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'].map((handle) => (
                            <span
                              key={handle}
                              className={`resize-handle ${handle}`}
                              onPointerDown={(event) => startDrag(event, box, handle)}
                            />
                          ))}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </section>

          <aside className="settings-panel">
            <div className="panel-section">
              <h2>{selectedBoxIsRegion ? 'Selected Table' : 'Selected Cut'}</h2>
              <div className="quad-fields">
                {['x', 'y', 'width', 'height'].map((field) => (
                  <label key={field}>
                    <span>{field}</span>
                    <input
                      type="number"
                      value={selectedBox ? Math.round(selectedBox[field]) : ''}
                      onChange={(event) => updateSelectedBox(field, event.target.value)}
                      disabled={!selectedBox}
                    />
                  </label>
                ))}
              </div>
            </div>

            <div className="panel-section">
              <h2>{selectedBoxIsRegion ? 'Table Tools' : 'Grid'}</h2>
              <div className="quad-fields">
                <label>
                  <span>cols</span>
                  <input
                    type="number"
                    value={gridSettings.cols}
                    min="1"
                    max="8"
                    onChange={(event) => setGridSettings((current) => ({ ...current, cols: event.target.value }))}
                  />
                </label>
                <label>
                  <span>rows</span>
                  <input
                    type="number"
                    value={gridSettings.rows}
                    min="1"
                    max="30"
                    onChange={(event) => setGridSettings((current) => ({ ...current, rows: event.target.value }))}
                  />
                </label>
                <label>
                  <span>gap x</span>
                  <input
                    type="number"
                    value={Math.round(gridSettings.gapX)}
                    onChange={(event) => setGridSettings((current) => ({ ...current, gapX: event.target.value }))}
                  />
                </label>
                <label>
                  <span>gap y</span>
                  <input
                    type="number"
                    value={Math.round(gridSettings.gapY)}
                    onChange={(event) => setGridSettings((current) => ({ ...current, gapY: event.target.value }))}
                  />
                </label>
              </div>
              <button className="btn btn-secondary full" type="button" onClick={findGridInsideRegions} disabled={preparing || !activePageRegion}>
                <Grid3x3 size={16} />
                Find Grid This Page
              </button>
              <button className="btn btn-secondary full" type="button" onClick={prepareSlips} disabled={preparing || !hasDetectedCuts}>
                <Scissors size={16} />
                Prepare Slips
              </button>
            </div>

            <div className="panel-section status-section">
              <h2>Ready Check</h2>
              <p>
                <Check size={15} />
                {isRegionMode ? 'Grid detection is limited to the active page.' : 'Final output uses only these visible cut boxes.'}
              </p>
              {error && <p className="error-text">{error}</p>}
            </div>
          </aside>
        </section>
      )}

      {showPrepared && (
        <section className="prepared-wrap">
          <div className="prepared-summary no-print">
            <p>{preparedCards.length} slips prepared</p>
            {customBooth && <strong>{customBooth}</strong>}
          </div>
          <div className="prepared-grid" id="printable-area">
            {preparedCards.map((card, index) => (
              <article className="prepared-card" key={`${card.pageNumber}-${index}`}>
                <img src={card.image} alt={`Prepared voter slip ${index + 1}`} />
                {customBooth && (
                  <div className="polling-footer">
                    Polling: <strong>{customBooth}</strong>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
