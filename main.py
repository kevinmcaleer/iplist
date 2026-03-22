import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse
from pydantic import BaseModel

from database import init_db, get_all_devices, update_device, delete_device
from scanner import scan_network_stream, get_subnets


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LAN Device Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/devices")
async def list_devices(online_only: bool = False):
    return get_all_devices(online_only=online_only)


@app.get("/api/scan")
async def trigger_scan():
    """SSE endpoint — streams each discovered device as an event."""
    subnets = get_subnets()

    def event_stream():
        # Tell the frontend which subnets we're scanning
        yield f"data: {json.dumps({'subnets': subnets})}\n\n"
        count = 0
        for device in scan_network_stream(subnets):
            count += 1
            yield f"data: {json.dumps(device)}\n\n"
        # Final event signals scan is complete
        yield f"data: {json.dumps({'done': True, 'scanned': count})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class DeviceUpdate(BaseModel):
    description: str | None = None
    hostname: str | None = None


@app.put("/api/devices/{mac}")
async def edit_device(mac: str, body: DeviceUpdate):
    if not update_device(mac, description=body.description, hostname=body.hostname):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True}


@app.delete("/api/devices/{mac}")
async def remove_device(mac: str):
    if not delete_device(mac):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True}
