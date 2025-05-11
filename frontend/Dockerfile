FROM node:18

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the app
COPY public ./public
COPY src ./src

# Expose and run
EXPOSE 3000
CMD ["npm", "start"]
