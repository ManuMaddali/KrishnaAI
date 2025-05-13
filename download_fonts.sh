#!/bin/bash

# This script downloads Poppins font files needed for the Flutter app

mkdir -p krishna_ai_app/fonts

echo "Downloading Poppins font files..."

# Download Regular
curl -L "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf" -o krishna_ai_app/fonts/Poppins-Regular.ttf

# Download Bold
curl -L "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf" -o krishna_ai_app/fonts/Poppins-Bold.ttf

# Download Light
curl -L "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Light.ttf" -o krishna_ai_app/fonts/Poppins-Light.ttf

echo "Poppins font files downloaded successfully!" 