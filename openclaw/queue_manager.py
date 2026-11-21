import json
import time
import os
import shutil
import subprocess
import threading
import logging
from pathlib import Path
import redis

logger = logging.getLogger("queue_manager")

class RedisConcurrencyQueue:
    """Redis-backed queue with strict concurrency=1 for heavy Remotion renders."""
    def __init__(self, host="127.0.0.1", port=6379, db=0, queue_name="remotion_renders"):
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.queue_name = queue_name
        self.is_running = False
        self.worker_thread = None

    def enqueue_render(self, job_data: dict) -> str:
        job_id = job_data.get("job_id", f"render_{int(time.time()*1000)}")
        job_data["job_id"] = job_id
        job_data["status"] = "queued"
        job_data["enqueued_at"] = time.time()
        
        # Save state
        self.r.set(f"job:{job_id}", json.dumps(job_data))
        # Push to queue list
        self.r.rpush(self.queue_name, job_id)
        logger.info(f"Enqueued Remotion job: {job_id}")
        return job_id

    def get_job(self, job_id: str) -> dict:
        raw = self.r.get(f"job:{job_id}")
        return json.loads(raw) if raw else None

    def start_worker(self, on_progress_callback=None):
        if self.is_running:
            return
        self.is_running = True
        self.on_progress = on_progress_callback
        self.worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Remotion Concurrency Worker started (concurrency=1)")

    def _process_loop(self):
        while self.is_running:
            # Blocking pop with 2s timeout
            item = self.r.blpop(self.queue_name, timeout=2)
            if not item:
                continue

            _, job_id = item
            raw_job = self.r.get(f"job:{job_id}")
            if not raw_job:
                continue

            job = json.loads(raw_job)
            self._execute_single_render(job)

    def _execute_single_render(self, job: dict):
        job_id = job["job_id"]
        job["status"] = "rendering"
        job["started_at"] = time.time()
        self.r.set(f"job:{job_id}", json.dumps(job))

        if self.on_progress:
            self.on_progress(job, "Iniciando renderização Remotion (--concurrency=1)...")

        output_filename = job.get("output_filename", f"{job_id}.mp4")
        output_path = f"/opt/video-benchmark/{output_filename}"
        composition = job.get("composition", "N1-remotion")

        npx_bin = shutil.which("npx") or "/usr/bin/npx"
        cmd = [
            npx_bin, "remotion", "render",
            composition,
            output_path,
            "--concurrency=1",
            "--gl=angle",
            "--log=warn"
        ]

        t0 = time.time()
        env = {**os.environ, "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
        try:
            p = subprocess.run(cmd, cwd="/opt/video-benchmark", capture_output=True, text=True, timeout=120, env=env)
            elapsed = round(time.time() - t0, 1)

            if p.returncode == 0 and Path(output_path).exists():
                job["status"] = "completed"
                job["output_path"] = output_path
                job["duration_s"] = elapsed
                job["file_size_kb"] = round(Path(output_path).stat().st_size / 1024, 1)
                logger.info(f"Render completed: {output_path} in {elapsed}s")
                if self.on_progress:
                    self.on_progress(job, f"Vídeo renderizado com sucesso em {elapsed}s ({job['file_size_kb']} KB)")
            else:
                job["status"] = "failed"
                job["error"] = p.stderr[:400]
                logger.error(f"Render failed: {p.stderr}")
                if self.on_progress:
                    self.on_progress(job, f"Falha na renderização: {p.stderr[:200]}")
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            if self.on_progress:
                self.on_progress(job, f"Erro na renderização: {str(e)}")

        job["finished_at"] = time.time()
        self.r.set(f"job:{job_id}", json.dumps(job))
