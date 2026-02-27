# Next.js Web App Dockerfile
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY apps/web/package.json ./
COPY package-lock.json ./
RUN npm install --ignore-scripts

# Copy application code
COPY apps/web/ ./

# Build arguments for environment
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run the application
CMD ["npm", "start"]
