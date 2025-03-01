# Use an official lightweight Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask runs on
EXPOSE 5000

# Command to run the app using Gunicorn (for production)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
