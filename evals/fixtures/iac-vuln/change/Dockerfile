FROM node:latest
WORKDIR /app
COPY . .
RUN curl -fsSL https://example-installer.invalid/setup.sh | sh
RUN npm install
CMD ["node", "server.js"]
