# Frontend Dockerfile - Technology Transformation Intelligence
# Node 20 with Vite dev server for local development

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files first for better Docker layer caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy application source code
COPY . .

# Expose the Vite dev server port
EXPOSE 5173

# Run Vite dev server with host flag to allow external access
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
