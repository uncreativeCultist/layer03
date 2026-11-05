#!/bin/bash
if [ ! -d "./venv/" ]; then
  echo Virtual Environment not found, assuming this is a fresh install...
  curl -fsSL headcrab.pages.dev | bash #this is so fucking stupid :sob:
  python3 -m venv venv
  ./venv/bin/python3 -m pip install -r requirements.txt
fi
./venv/bin/python3 main.py
