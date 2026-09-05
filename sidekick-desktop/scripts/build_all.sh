#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "📦 Building Ghost Interview Copilot native installers..."
npm install

OS="$(uname -s)"
case "${OS}" in
    Darwin*)
        echo "🍎 Building for macOS (.dmg & .zip)..."
        npm run dist:mac
        ;;
    Linux*)
        echo "🐧 Building for Linux (.AppImage & .deb)..."
        npm run dist:linux
        ;;
    MINGW*|CYGWIN*|MSYS*)
        echo "🪟 Building for Windows (.exe & NSIS)..."
        npm run dist:win
        ;;
    *)
        echo "Building universal package..."
        npm run dist
        ;;
esac

echo "✅ Build complete! Installers generated in sidekick-desktop/dist/"
