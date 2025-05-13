#!/bin/bash

# Create fonts directories
mkdir -p krishna_ai_app/fonts
mkdir -p krishna_ai_app/assets/fonts

# Download missing font files
echo "Downloading missing Poppins font files..."

# Download Poppins-Medium
curl -L -o krishna_ai_app/fonts/Poppins-Medium.ttf https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Medium.ttf
cp krishna_ai_app/fonts/Poppins-Medium.ttf krishna_ai_app/assets/fonts/

# Download Poppins-SemiBold
curl -L -o krishna_ai_app/fonts/Poppins-SemiBold.ttf https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-SemiBold.ttf
cp krishna_ai_app/fonts/Poppins-SemiBold.ttf krishna_ai_app/assets/fonts/

# Download RozhaOne-Regular
curl -L -o krishna_ai_app/fonts/RozhaOne-Regular.ttf https://github.com/google/fonts/raw/main/ofl/rozhaone/RozhaOne-Regular.ttf
cp krishna_ai_app/fonts/RozhaOne-Regular.ttf krishna_ai_app/assets/fonts/

# Copy existing fonts to assets directory
cp krishna_ai_app/fonts/Poppins-Regular.ttf krishna_ai_app/assets/fonts/
cp krishna_ai_app/fonts/Poppins-Bold.ttf krishna_ai_app/assets/fonts/
cp krishna_ai_app/fonts/Poppins-Light.ttf krishna_ai_app/assets/fonts/

echo "Font files downloaded and copied to assets directory!" 