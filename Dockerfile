# Use official Node.js image
FROM node:18

# Set working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first
COPY node-app/package*.json ./

# Install dependencies
RUN npm install

# Copy the entire application
COPY node-app/ .  

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["npm", "start"]
