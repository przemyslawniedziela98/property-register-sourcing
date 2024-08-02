#!/bin/bash
if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Creating a new one."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
python evidence_book_sourcing.py
deactivate