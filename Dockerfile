# Use the official Python 3.12 image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first
COPY requirements.txt requirements.txt

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your code (app.py, etc.) into the container
COPY . .

# Tell the cloud to run your app using the gunicorn server
# It will run the 'app' variable from your 'app.py' file
# It will listen on port 8080, which App Hosting expects
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]