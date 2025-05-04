# የቀሲስ ጥላሁን ጉደታ የንስሐ ልጆች አቅሌስያ Telegram Bot

A Telegram bot for managing appointments, communion requests, and communication with father confesor.

## Features

- User Registration and Profile Management
- Appointment Booking System
- Communion Request Management
- Question and Feedback System
- Admin Dashboard for:
  - Managing Appointments
  - Handling Communion Requests
  - Viewing and Responding to Questions
  - Managing Availability Schedule

## Prerequisites

- Python 3.7+
- PostgreSQL Database
- Telegram Bot Token

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Create and activate a virtual environment:
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_TELEGRAM_ID=comma_separated_admin_ids
DATABASE_URL=your_postgresql_connection_string
```

5. Initialize the database:
```bash
psql -f migration.sql
```

## Running the Bot

```bash
python bot.py
```

## Available Commands

### User Commands
- `/start` - Start the bot
- `/register` - Register a new account
- `/book` - Schedule an appointment
- `/profile` - View your profile
- `/mybookings` - View your appointments
- `/communion` - Request communion
- `/questions` - Submit questions or feedback

### Admin Commands
- `/appointments` - View all appointments
- `/addavailability` - Add available time slots
- `/availability` - Manage availability schedule
- `/question` - View submitted questions
- `/communions` - Manage communion requests

## Docker Support

The project includes Docker support for easy deployment:

```bash
docker build -t aklesia-bot .
docker run -d --env-file .env aklesia-bot
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
