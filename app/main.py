from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from app.routes import snomed_route

app = FastAPI()

app.include_router(snomed_route.router, prefix="/api")

# Serve React static files
frontend_build_path = os.path.join(os.path.dirname(__file__), "../frontend/build")
if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_path, "static")), name="static")

    @app.get("/{path_name:path}")
    async def serve_react_app(path_name: str):
        # Serve the React app's index.html for any unmatched routes
        return FileResponse(os.path.join(frontend_build_path, "index.html"))
else:
    print("Warning: React build folder not found. Run 'npm run build' in the frontend directory.")
