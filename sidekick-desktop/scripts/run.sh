#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "🚀 Starting Ghost Interview Copilot Desktop App..."
if [ ! -d "node_modules" ]; then
    echo "📦 Installing desktop dependencies..."
    npm install
fi

npm start
