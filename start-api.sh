#!/bin/bash
cd "$(cd "$(dirname "$0")" && pwd)/backend"
source venv/bin/activate
flask --app app run --host=0.0.0.0 --port=5001 --debug
