"""Loopback-only local inference service. Original media is never persisted."""
from contextlib import asynccontextmanager
from pathlib import Path
import json
import tempfile
import asyncio
import sys
import os
import time
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from model import AudioModel, ROOT, ARTIFACTS, MODEL_VERSION, LABELS, LABEL_NAMES, read_audio
from caption_service import CaptionInput, CaptionError, configuration_status, generate_caption, load_local_configuration
from local_caption_runtime import ensure_local_runtime, stop_owned_runtime
from room_service import room_status, analyze_room, RoomError

load_local_configuration()

WEB = ROOT.parent.parent / 'outputs' / 'meowmemo-prototype'
model = None
inference_slot = asyncio.Semaphore(1)


@asynccontextmanager
async def lifespan(app):
    global model
    print('Loading local audio model on CPU. No cloud connection or API key.', flush=True)
    caption_runtime = await run_in_threadpool(ensure_local_runtime)
    model = await run_in_threadpool(AudioModel)
    print('Local model ready.', flush=True)
    try:
        yield
    finally:
        await run_in_threadpool(stop_owned_runtime, caption_runtime)


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    origin = request.headers.get('origin')
    if host not in ('127.0.0.1', 'localhost', 'testserver'):
        return JSONResponse({'detail': 'Local access only.'}, status_code=403)
    if request.method == 'POST' and origin and origin != f'http://{request.headers.get("host")}':
        return JSONResponse({'detail': 'Open MeowMemo on this local server to analyze.'}, status_code=403)
    if int(request.headers.get('content-length', '0')) > 51 * 1024 * 1024:
        return JSONResponse({'detail': 'Maximum upload size: 50 MB.'}, status_code=413)
    response = await call_next(request)
    # Source changes should appear without clearing browser storage.
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/api/health')
def health():
    return {'ready': model is not None, 'modelVersion': MODEL_VERSION, 'offline': True,
            'device': 'Apple M5 / CPU', 'cloudApiConnected': configuration_status()['available'] and not configuration_status().get('localOnly'),
            'audioInferenceOffline': True, 'captionProvider': configuration_status()['provider'],
            'cloudCaptionsConfigured': configuration_status()['available'] and not configuration_status().get('localOnly')}


@app.get('/api/model')
def info():
    report = json.loads((ARTIFACTS / 'evaluation.json').read_text())
    return {'version': MODEL_VERSION, 'featureMode': report['feature_mode'],
            'labels': LABEL_NAMES, 'testSamples': report['test_samples'],
            'testCats': len(report['test_cats']), 'test': report['heldout_test_before_abstention'],
            'status': 'experimental', 'notice': report['warning']}


@app.get('/api/captions/status')
def caption_status():
    return configuration_status()


@app.post('/api/captions')
async def caption(data: CaptionInput):
    try:
        return await run_in_threadpool(generate_caption, data)
    except CaptionError as e:
        return JSONResponse({'detail': e.message, 'code': e.code}, status_code=e.status)


@app.get('/api/rooms/status')
def room_ai_status():
    return room_status()


@app.post('/api/rooms/analyze')
async def room_photo(request: Request, file: UploadFile = File(...)):
    raw = await file.read(10 * 1024 * 1024 + 1)
    try:
        return await run_in_threadpool(analyze_room, raw, request.query_params.get('roomType', 'living'))
    except RoomError as e:
        return JSONResponse({'detail': e.message}, status_code=e.status)
    finally:
        await file.close()


@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...)):
    async with inference_slot:
        try:
            with tempfile.TemporaryDirectory(prefix='meowmemo-audio-') as directory:
                path = Path(directory) / 'original-clip'
                size = 0
                with path.open('wb') as out:
                    while chunk := await file.read(1024 * 1024):
                        size += len(chunk)
                        if size > 50 * 1024 * 1024:
                            raise HTTPException(413, 'Maximum upload size: 50 MB.')
                        out.write(chunk)
                if not size:
                    raise HTTPException(400, 'Please choose an audio or video recording.')
                return await run_in_threadpool(model.predict_file, path)
        except (ValueError, RuntimeError) as e:
            raise HTTPException(400, str(e)) from e
        except __import__('subprocess').TimeoutExpired as e:
            raise HTTPException(400, 'Audio decoding timed out. Try a smaller clip.') from e
        finally:
            await file.close()


def public_samples():
    # Explicit listening examples, not selected by prediction correctness.
    # Evaluation still covers the original full held-out test set.
    return json.loads((ROOT / 'samples.json').read_text())


@app.get('/api/samples')
def samples():
    return public_samples()


@app.get('/api/samples/{sample_id}/audio')
def sample_audio(sample_id: str):
    item = next((s for s in public_samples() if s['id'] == sample_id), None)
    if not item:
        raise HTTPException(404, 'Unknown public sample.')
    return FileResponse(ROOT / 'data' / 'listening-previews' / item['playbackFile'],
                        media_type='audio/wav', filename=item['playbackFile'])


@app.get('/api/samples/{sample_id}/original')
def original_sample_audio(sample_id: str):
    item = next((s for s in public_samples() if s['id'] == sample_id), None)
    if not item:
        raise HTTPException(404, 'Unknown public sample.')
    return FileResponse(ROOT / 'data' / item['directory'] / item['name'],
                        media_type='audio/wav', filename=item['name'])


@app.post('/api/samples/{sample_id}/analyze')
async def sample_analyze(sample_id: str):
    item = next((s for s in public_samples() if s['id'] == sample_id), None)
    if not item:
        raise HTTPException(404, 'Unknown public sample.')
    async with inference_slot:
        result = await run_in_threadpool(model.predict_file, ROOT / 'data' / item['directory'] / item['name'])
    return {'sample': item, 'analysis': result}


@app.get('/ai-lab')
def lab():
    return FileResponse(ROOT / 'demo.html')


# Serve existing UI on the SAME origin/port; existing IndexedDB data stays intact.
app.mount('/', StaticFiles(directory=WEB, html=True), name='prototype')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(sys.argv[1]) if len(sys.argv) > 1 else 8765, log_level='info')
