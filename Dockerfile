# a python application dockerfile 
FROM python:3.13-slim
# Set the working directory
WORKDIR /app
# Copy the requirements file into the container 
COPY requirements.txt .
# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application code into the container
COPY . . 
# Expose the port the app runs on
EXPOSE 8000
# start the application
CMD ["python", "bot.py"]