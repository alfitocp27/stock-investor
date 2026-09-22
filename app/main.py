import uvicorn
from fastapi import FastAPI
from app.web.routes import router
from app.data.models import get_engine, get_session, Base
from app import scheduler

app = FastAPI(title="Stock Investor", description="Personal Low-Risk IDX Investment Advisor")
app.include_router(router)

@app.on_event("startup")
def on_startup():
    engine = get_engine()
    Base.metadata.create_all(engine)

@app.get("/health")
async def health():
    return {"status": "ok"}

def start_scheduler():
    import atexit
    from apscheduler.schedulers.background import BackgroundScheduler
    
    def scheduled_scan_job():
        session = get_session()
        try:
            scheduler.run_full_scan(session)
        finally:
            session.close()

    sched = BackgroundScheduler()
    sched.add_job(scheduled_scan_job, "cron", hour=8, minute=0)
    sched.start()
    atexit.register(lambda: sched.shutdown(wait=False))

if __name__ == "__main__":
    start_scheduler()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
