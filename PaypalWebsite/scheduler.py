from flask_apscheduler import APScheduler
from PaypalWebsite.website import app, purge_users

# Configure scheduler
class Config:
    SCHEDULER_API_ENABLED = True 
    SCHEDULER_TIMEZONE = "America/New_York"


app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)

# Every 24 hours (at 3:30AM)
# Purge Temp Users that are 7+ days old
scheduler.add_job(
    id='daily_user_purge',
    args=(7,),
    func=purge_users,
    trigger='cron',
    hour=3,
    minute=30           
)
scheduler.start()