#!/bin/bash

# Icons and names
ICONS=(
  "icon_16x16.png:16x16"
  "icon_16x16@2x.png:32x32"
  "icon_32x32.png:32x32"
  "icon_32x32@2x.png:64x64"
  "icon_64x64.png:64x64"
  "icon_64x64@2x.png:128x128"
  "icon_128x128.png:128x128"
  "icon_128x128@2x.png:256x256"
  "icon_256x256.png:256x256"
  "icon_256x256@2x.png:512x512"
  "icon_512x512.png:512x512"
  "icon_512x512@2x.png:1024x1024"
)

# Create directory and icons
generate_icons() {
  local src_image=$1
  local output_dir=$2
  local resize=$3

  mkdir -p "$output_dir"

  for ICON in "${ICONS[@]}"; do
    IFS=":" read -r NAME SIZE <<< "$ICON"
    if [[ "$resize" == "true" ]]; then
      convert "$src_image" -resize "$SIZE" "$output_dir/$NAME"
    else
      convert -size "$SIZE" xc:none "$output_dir/$NAME"
    fi
  done

  echo "Images created at path: $output_dir"
}

# Create .icns file
create_icns() {
  # Directory containing images(current directory)
  IMAGE_DIR="$(pwd)"

  # Check if needed files exist
  for ICON in "${ICONS[@]}"; do
    IFS=":" read -r NAME SIZE <<< "$ICON"
    if [[ ! -f "$IMAGE_DIR/$NAME" ]]; then
      echo "Fout: $NAME ontbreekt in $IMAGE_DIR"
      exit 1
    fi
  done

  # Create iconset directory
  ICONSET_DIR="icon.iconset"
  mkdir -p "$ICONSET_DIR"

  # Copy images to the iconset directory
  for ICON in "${ICONS[@]}"; do
    IFS=":" read -r NAME SIZE <<< "$ICON"
    cp "$IMAGE_DIR/$NAME" "$ICONSET_DIR/"
  done

  # Turn into .icns bestand
  icnsutil -c icns "$ICONSET_DIR"

  # Validate if the .icns file has been created
  if [[ -f "icon.icns" ]]; then
    echo "The .icns was succesfully created."
  else
    echo "There was a problem while creating the .icns file."
    exit 1
  fi
}

# Help function
show_help() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  --create-placeholders               Create placeholders"
  echo "  --create-placeholders-from-image    Create placeholders from exiting image"
  echo "  --create-icns                       Create .icns from images"
  echo "  --help                              Show this help"
}

# Check arguments
if [[ $# -eq 0 ]]; then
  show_help
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --create-placeholders)
      generate_icons "" "$(pwd)/icon_images" "false"
      shift
      ;;
    --create-placeholders-from-image)
      if [[ -z "$2" ]]; then
        echo "Usage: $0 --create-placeholders-from-image <imagepath>"
        exit 1
      fi
      generate_icons "$2" "$(pwd)/icon_images" "true"
      shift 2
      ;;
    --create-icns)
      create_icns
      shift
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done
