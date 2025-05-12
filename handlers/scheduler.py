from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from db import cursor, conn


# Initialize scheduler (add this at the top of the file)
scheduler = AsyncIOScheduler()

async def add_default_days():
    """Adds default available days (Wednesdays & Fridays) for the next 14 days."""
    today = datetime.now().date()
    next_14_days = [today + timedelta(days=i) for i in range(14)]
    default_days = [d for d in next_14_days if d.weekday() in [2, 4]]  # Wed (2), Fri (4)

    for day in default_days:
        cursor.execute("""
            INSERT INTO available_days (appointment_date, max_slots, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (appointment_date) DO NOTHING
        """, (day, 15, 'active'))
    conn.commit()
    print(f"✅ Added default days: {default_days}")

# Start the scheduler (call this when your bot starts)
def start_scheduler():
    scheduler.add_job(
        add_default_days,
        trigger=CronTrigger(day_of_week="fri", hour=20, minute=0),  # Every Friday at 20:00
        timezone="Africa/Addis_Ababa"  # Adjust timezone if needed
    )
    scheduler.start()